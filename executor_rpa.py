import os
import time
import random
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timezone, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.parse # <-- IMPORTAÇÃO CORRIGIDA AQUI
from dotenv import load_dotenv
from supabase import create_client, Client
from playwright.sync_api import sync_playwright
from google import genai
from google.genai import types

load_dotenv()

# ==========================================
# ⏰ PARÂMETROS DE HORÁRIO COMERCIAL E ALERTAS
# ==========================================
DIAS_PERMITIDOS = [0, 1, 2, 3, 4] 
HORA_INICIO = 8  
HORA_FIM = 17    
MEU_WHATSAPP = os.getenv("WHATSAPP_EMPRESA")
MEU_EMAIL_ALERTA = os.getenv("EMAIL_EMPRESA")

def verificar_horario_comercial():
    fuso_brasilia = timezone(timedelta(hours=-3))
    agora_br = datetime.now(fuso_brasilia)
    if agora_br.weekday() in DIAS_PERMITIDOS and HORA_INICIO <= agora_br.hour < HORA_FIM:
        return True, agora_br
    return False, agora_br

# ==========================================
# CONFIGURAÇÕES E CREDENCIAIS
# ==========================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
EMAIL_SENHA = os.getenv("EMAIL_SENHA") # Mesma senha de app usada no SMTP funciona no IMAP
PROFILE_DIR = "./whatsapp_session"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client_ia = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 🧠 MÓDULO DE INTELIGÊNCIA: ANÁLISE DE RESPOSTA
# ==========================================
def analisar_intencao_resposta(texto_resposta):
    """Usa o Gemini para ler a resposta do lead e classificar a intenção."""
    if not texto_resposta: return False
    
    prompt = f"""
    Analise a seguinte resposta recebida de um lead B2B durante uma prospecção:
    "{texto_resposta}"
    
    A intenção do lead é POSITIVA (demonstra algum nível de interesse, quer marcar reunião, pede mais informações ou respondeu de forma aberta a conversar)? 
    Responda ESTRITAMENTE com "SIM" ou "NAO".
    """
    try:
        resposta = client_ia.models.generate_content(
            model='gemini-2.5-flash', contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        return "SIM" in resposta.text.strip().upper()
    except:
        return True # Em caso de dúvida/erro da API, assumimos positivo para você avaliar manualmente

# ==========================================
# 🚨 MÓDULO DE ALERTAS
# ==========================================
def disparar_alerta_sucesso(page_whatsapp, nome_lead, empresa, canal, email_lead, linkedin_lead, texto_resposta):
    agora = datetime.now().strftime('%d/%m/%Y às %H:%M')
    mensagem = (
        f"🚨 *ALERTA DE CONVERSÃO B2B* 🚨\n\n"
        f"O lead *{nome_lead}* da empresa *{empresa}* acabou de responder de forma POSITIVA pelo *{canal}*!\n\n"
        f"🕒 Data/Hora: {agora}\n"
        f"📧 E-mail do Lead: {email_lead}\n"
        f"🔗 LinkedIn: {linkedin_lead}\n\n"
        f"💬 *Resposta do Lead:*\n\"{texto_resposta}\"\n\n"
        f"A cadência automática foi pausada. Assuma o atendimento!"
    )
    
    print(f"\n🔔 DISPARANDO ALERTAS PARA O CHEFE: {empresa} respondeu!")
    
    # 1. Alerta por E-mail
    enviar_email(MEU_EMAIL_ALERTA, f"🚨 LEAD QUENTE: {empresa} Respondeu via {canal}", mensagem)
    
    # 2. Alerta por WhatsApp usando Playwright
    try:
        texto_codificado = urllib.parse.quote(mensagem)
        link_envio = f"https://web.whatsapp.com/send?phone={MEU_WHATSAPP}&text={texto_codificado}"
        page_whatsapp.goto(link_envio)
        page_whatsapp.wait_for_selector('span[data-icon="send"]', timeout=30000)
        time.sleep(2)
        page_whatsapp.locator('span[data-icon="send"]').first.click()
        time.sleep(3)
        print("   ✅ Alerta enviado para o seu WhatsApp!")
    except Exception as e:
        print(f"   ⚠️ Erro ao enviar alerta de WhatsApp: {e}")

# ==========================================
# 👁️ SENTINELAS DE RESPOSTA (IMAP E LINKEDIN)
# ==========================================
def ler_emails_nao_lidos():
    """Conecta no Gmail (IMAP) e lê e-mails não lidos buscando respostas de leads."""
    print("   📧 [Sentinela IMAP] Checando caixa de entrada do E-mail...")
    respostas_encontradas = []
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_REMETENTE, EMAIL_SENHA)
        mail.select("inbox")
        
        # Busca e-mails não lidos
        status, mensagens = mail.search(None, "UNSEEN")
        if status != "OK" or not mensagens[0]: return []
        
        ids_emails = mensagens[0].split()
        for i in ids_emails:
            _, dados = mail.fetch(i, "(RFC822)")
            for resposta_part in dados:
                if isinstance(resposta_part, tuple):
                    msg = email.message_from_bytes(resposta_part[1])
                    remetente = msg.get("From")
                    email_extraid = remetente.split("<")[-1].replace(">", "").strip() if "<" in remetente else remetente
                    
                    corpo = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                corpo = part.get_payload(decode=True).decode()
                                break
                    else:
                        corpo = msg.get_payload(decode=True).decode()
                        
                    respostas_encontradas.append({"email": email_extraid, "texto": corpo[:500]})
    except Exception as e:
        print(f"   ⚠️ Erro no IMAP: {e}")
    return respostas_encontradas

def ler_respostas_linkedin(page):
    """Abre o Inbox do LinkedIn e verifica se há mensagens novas."""
    print("   🔗 [Sentinela LinkedIn] Checando Inbox do LinkedIn...")
    respostas = []
    try:
        page.goto("https://www.linkedin.com/messaging/")
        time.sleep(5)
        
        # Procura por conversas com indicador de 'não lida' (bolinha azul do LinkedIn)
        # O seletor pode precisar de ajuste fino conforme o idioma/layout do seu LinkedIn
        nao_lidas = page.locator("li:has(div[aria-label*='não lida']), li:has(div[aria-label*='unread'])")
        count = nao_lidas.count()
        
        for i in range(count):
            conversa = nao_lidas.nth(i)
            conversa.click() # Abre a conversa
            time.sleep(3)
            
            # Pega o nome do remetente e a última mensagem
            nome_remetente = page.locator("h2[class*='msg-thread__topcard-title']").first.inner_text()
            ultima_mensagem = page.locator("p[class*='msg-s-event-listitem__body']").last.inner_text()
            
            respostas.append({"nome": nome_remetente, "texto": ultima_mensagem})
    except Exception as e:
        print("   ⚠️ Sem mensagens novas no LinkedIn ou erro de layout.")
    return respostas

# ==========================================
# FUNÇÕES DE DISPARO (RPA)
# ==========================================
def enviar_email(destino, assunto, corpo):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = destino
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'plain'))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        server.sendmail(EMAIL_REMETENTE, destino, msg.as_string())
        server.quit()
        return True
    except: return False

def linkedin_rpa(page, url_perfil, acao, texto=""):
    if not url_perfil or "linkedin.com" not in url_perfil: return False
    print(f"   🤖 [RPA LinkedIn] Executando '{acao}' em: {url_perfil}")
    page.goto(url_perfil)
    time.sleep(5) 
    
    try:
        if acao == "curtir":
            page.goto(f"{url_perfil.rstrip('/')}/recent-activity/all/")
            time.sleep(5)
            page.locator("button[aria-label*='Gostar'], button[aria-label*='Like']").first.click()
            time.sleep(3)
            return True
        elif acao == "conectar":
            conectar_btn = page.locator("button:has-text('Conectar'), button:has-text('Connect')").first
            if conectar_btn.is_visible(): conectar_btn.click()
            else:
                page.locator("button[aria-label='Mais ações'], button[aria-label='More actions']").first.click()
                time.sleep(1)
                page.locator("div[role='button']:has-text('Conectar')").first.click()
            time.sleep(2)
            page.locator("button:has-text('Adicionar nota'), button:has-text('Add a note')").first.click()
            time.sleep(1)
            page.fill("textarea[name='message']", texto)
            time.sleep(2)
            page.locator("button:has-text('Enviar'), button:has-text('Send')").first.click()
            return True
        elif acao == "mensagem":
            page.locator("button:has-text('Mensagem'), button:has-text('Message')").first.click()
            time.sleep(3)
            page.fill("div[role='textbox']", texto)
            time.sleep(1)
            page.locator("button[type='submit']").first.click()
            return True
        elif acao == "visitar":
            return True
    except: return False

# ==========================================
# MOTOR EXECUTOR DIÁRIO
# ==========================================
def executar_rotina_diaria():
    print("==================================================")
    print("🟢 MOTOR RPA E FECHAMENTO DE LOOP INICIADO 🟢")
    print("==================================================\n")
    
    permitido, agora_br = verificar_horario_comercial()
    
    if not permitido:
        print("⛔ ALERTA: Fora do Horário Comercial. Encerrando rotina...")
        return
    
    # ---------------------------------------------------------
    # FASE 1: FECHAMENTO DE LOOP (VERIFICAR RESPOSTAS)
    # ---------------------------------------------------------
    # ---------------------------------------------------------
    # FASE 1: FECHAMENTO DE LOOP (VERIFICAR RESPOSTAS)
    # ---------------------------------------------------------
    print("🔍 FASE 1: Verificando se algum lead respondeu...\n")
    
    # Busca leads ativos no banco para cruzamento
    resp_leads = supabase.table("leads_hunter").select("*").eq("status_funil", "Prospecção").execute()
    leads_ativos = resp_leads.data
    
    # 1. Verifica E-mails
    emails_recebidos = ler_emails_nao_lidos()
    
    print("\n🌐 Abrindo Instância Playwright disfarçada (Anti-Bloqueio)...")
    p_context = sync_playwright().start()
    
    # 👇 A MÁGICA CONTRA O BLOQUEIO DO LINKEDIN ESTÁ AQUI 👇
    browser = p_context.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR, 
        headless=False,
        channel="chrome", # Usa o motor do Google Chrome real instalado no seu PC
        args=["--disable-blink-features=AutomationControlled"] # Esconde a identidade de robô
    )
    
    paginas = browser.pages
    page_lkdn = paginas[0] if len(paginas) > 0 else browser.new_page()
    page_wpp = browser.new_page() 
    
    print("   Carregando LinkedIn...")
    # timeout maior e wait_until impede que o robô trave esperando anúncios carregarem
    page_lkdn.goto("https://www.linkedin.com", wait_until="domcontentloaded", timeout=90000)
    
    print("   Carregando WhatsApp Web...")
    page_wpp.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=90000)
    
    # ========================================================
    # 🛑 FREIO DE MÃO PARA LOGIN (AQUECIMENTO DE SESSÃO) 🛑
    # ========================================================
    print("\n" + "="*50)
    print("🛑 PAUSA DE SEGURANÇA (AQUECIMENTO) 🛑")
    print("O robô carregou os sites e está congelado. Aproveite este momento para:")
    print("1. Ir na aba do LinkedIn e fazer o seu login.")
    print("2. Ir na aba do WhatsApp Web e garantir que está logado.")
    print("="*50)
    
    input("👉 Quando as duas abas estiverem logadas, clique aqui no terminal e pressione [ENTER] para continuar... ")
    print("✅ Sessões prontas! Retomando a execução...\n")    
    # ========================================================

    # 2. Verifica LinkedIn
    mensagens_linkedin = ler_respostas_linkedin(page_lkdn)
    
    # 3. Cruzamento e Análise de Intenção
    for lead in leads_ativos:
        resposta_detectada = ""
        canal_resposta = ""
        
        # Procura match no E-mail
        for email_msg in emails_recebidos:
            if lead.get('email') and lead['email'].lower() in email_msg['email'].lower():
                resposta_detectada = email_msg['texto']
                canal_resposta = "E-mail"
                
        # Procura match no LinkedIn (procura pelo nome ou parte do nome)
        for msg_lkdn in mensagens_linkedin:
            if lead.get('nome_socio') and lead['nome_socio'].split()[0].lower() in msg_lkdn['nome'].lower():
                resposta_detectada = msg_lkdn['texto']
                canal_resposta = "LinkedIn"
        
        # Se achou resposta, passa pelo Gemini
        if resposta_detectada:
            if analisar_intencao_resposta(resposta_detectada):
                # MATAR A CADÊNCIA
                supabase.table("leads_hunter").update({"status_funil": "Respondeu"}).eq("id", lead['id']).execute()
                
                # ENVIAR ALERTAS
                disparar_alerta_sucesso(
                    page_wpp, lead['nome_socio'], lead['nome_empresa'], canal_resposta, 
                    lead.get('email'), lead.get('links_redes_sociais', {}).get('linkedin_decisor'), resposta_detectada
                )

    # ---------------------------------------------------------
    # FASE 2: EXECUÇÃO DA CADÊNCIA
    # ---------------------------------------------------------
    hoje_str = agora_br.strftime('%Y-%m-%d')
    print("\n🔍 FASE 2: Consultando banco de dados por tarefas agendadas...")
    
    try:
        resposta = supabase.table("cadencia_agendada") \
            .select("*, leads_hunter(status_funil)") \
            .lte("data_agendada", hoje_str) \
            .eq("status", "Pendente") \
            .execute()
        tarefas_do_banco = resposta.data
    except Exception as e:
        print(f"❌ Erro ao conectar com Supabase: {e}")
        if p_context: p_context.stop()
        return

    if not tarefas_do_banco:
        print("✅ Nenhuma tarefa pendente para hoje.")
    else:
        print(f"\n📅 Foram encontradas {len(tarefas_do_banco)} tarefas na fila para hoje.")
        
        for tarefa in tarefas_do_banco:
            id_tarefa = tarefa['id']
            lead_status = tarefa['leads_hunter']['status_funil'] if tarefa.get('leads_hunter') else "Prospecção"
            
            if lead_status == "Respondeu":
                print(f"\n🛑 KILL SWITCH: Ignorando tarefa de {tarefa['empresa_lead']}. (Cliente já respondeu)")
                supabase.table("cadencia_agendada").update({"status": "Cancelado"}).eq("id", id_tarefa).execute()
                continue
                
            print(f"\n▶️ Executando [{tarefa['tipo_acao'].upper()}] para {tarefa['empresa_lead']}...")
            
            sucesso = False
            if tarefa['tipo_acao'] == "email":
                sucesso = enviar_email(tarefa['contato_alvo'], tarefa.get('assunto_email', ''), tarefa.get('copy_mensagem', ''))
            elif tarefa['tipo_acao'] in ['visitar', 'curtir', 'conectar', 'mensagem']:
                sucesso = linkedin_rpa(page_lkdn, tarefa['contato_alvo'], tarefa['tipo_acao'], tarefa.get('copy_mensagem', ''))
                
                if sucesso:
                    minutos_espera = random.randint(4, 12)
                    print(f"   ⏳ Pausa de segurança de {minutos_espera} minutos...")
                    time.sleep(minutos_espera * 60)
                
            if sucesso:
                print("   💾 Tarefa concluída! Atualizando Supabase...")
                supabase.table("cadencia_agendada").update({"status": "Concluido"}).eq("id", id_tarefa).execute()
    
    if p_context:
        p_context.stop()
    print("\n🏁 ROTINA DIÁRIA CONCLUÍDA COM SUCESSO!")

if __name__ == "__main__":
    executar_rotina_diaria()