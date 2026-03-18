import os
import sys
import time
import random
import smtplib
import requests
import json
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from playwright.sync_api import sync_playwright
from google import genai
from google.genai import types

load_dotenv()

# --- CONEXÃO SUPABASE E APIs ---
def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

sb = get_supabase()
client_ia = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROFILE_DIR = "./agente_farmer_session"

# ==========================================
# 1. MÓDULO DE ÁUDIO "PLUG AND PLAY"
# ==========================================
MOTOR_DE_VOZ = os.getenv("MOTOR_DE_VOZ", "elevenlabs").lower()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
URL_VOZ_INTERNA = os.getenv("URL_VOZ_INTERNA")

def gerar_audio_dinamico(texto, voice_id):
    """
    Roteador de Inteligência de Voz. 
    Decide qual motor usar com base no arquivo .env para facilitar a escala futura.
    """
    if MOTOR_DE_VOZ == "elevenlabs":
        return _gerar_via_elevenlabs(texto, voice_id)
    elif MOTOR_DE_VOZ == "interno":
        return _gerar_via_servidor_proprio(texto, voice_id)
    else:
        print("   ❌ Motor de voz desconhecido no .env! Use 'elevenlabs' ou 'interno'.")
        return None

def _gerar_via_elevenlabs(texto, voice_id):
    if not ELEVENLABS_API_KEY or not voice_id: return None
    print("   🎙️ [IA] Gerando áudio clonado via ElevenLabs (Nuvem)...")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": texto,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            caminho_arquivo = "audio_temp.mp3"
            with open(caminho_arquivo, "wb") as f:
                f.write(response.content)
            return caminho_arquivo
        else:
            print(f"   ❌ Erro ElevenLabs: {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ Erro na geração de áudio: {e}")
        return None

def _gerar_via_servidor_proprio(texto, voice_id):
    """ 
    Motor pronto para o futuro. Quando você subir sua GPU com o XTTS v2, 
    ele baterá na sua própria API gratuita.
    """
    if not URL_VOZ_INTERNA: 
        print("   ❌ URL_VOZ_INTERNA não configurada no .env.")
        return None
        
    print("   🎙️ [IA] Gerando áudio via Servidor Próprio (Custo Zero)...")
    try:
        dados = {'texto': texto, 'voice_id': voice_id}
        resposta = requests.post(URL_VOZ_INTERNA, json=dados)
        
        if resposta.status_code == 200:
            caminho_novo_audio = "audio_temp.wav"
            with open(caminho_novo_audio, "wb") as f: 
                f.write(resposta.content)
            return caminho_novo_audio
        else:
            print(f"   ❌ Erro Servidor Próprio: {resposta.text}")
    except Exception as e: 
        print(f"   ❌ Erro de conexão com o Servidor Interno: {e}")
    return None

def enviar_audio_whatsapp(page, caminho_audio):
    """Faz o Playwright clicar no anexo do WhatsApp e enviar o arquivo de áudio."""
    try:
        page.locator('div[title="Anexar"], span[data-icon="plus"]').first.click()
        time.sleep(1)
        page.set_input_files('input[type="file"]', caminho_audio)
        time.sleep(2)
        page.locator('span[data-icon="send"]').first.click()
        time.sleep(5) 
        os.remove(caminho_audio)
        return True
    except Exception as e:
        print(f"   ❌ Erro ao enviar áudio no WhatsApp: {e}")
        return False

# ==========================================
# 2. FUNÇÕES DE TEXTO E E-MAIL
# ==========================================
def enviar_email_smtp(cliente, destino, assunto, corpo):
    remetente = cliente.get('email_remetente_disparo')
    senha = cliente.get('senha_email_disparo')
    if not remetente or not senha: return False
    try:
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destino
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'plain'))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(remetente, senha)
        server.sendmail(remetente, destino, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"   ❌ Erro ao enviar e-mail: {e}")
        return False

def enviar_whatsapp_humano(page, telefone, mensagem):
    tel_limpo = ''.join(filter(str.isdigit, str(telefone)))
    if not tel_limpo.startswith("55"): tel_limpo = f"55{tel_limpo}"
    
    print(f"   🟢 [WhatsApp] Acessando conversa com {tel_limpo}...")
    page.goto(f"https://web.whatsapp.com/send?phone={tel_limpo}")
    
    try:
        caixa_texto = page.wait_for_selector('div[title="Digite uma mensagem"], div[title="Type a message"]', timeout=40000)
        time.sleep(random.uniform(3.0, 6.0))
        caixa_texto.click()
        page.keyboard.type(mensagem, delay=random.uniform(40, 90)) 
        time.sleep(random.uniform(1.0, 3.0))
        page.locator('span[data-icon="send"]').first.click()
        time.sleep(random.uniform(4.0, 7.0))
        return True
    except Exception as e:
        print(f"   ❌ Erro no WhatsApp: {e}")
        return False

# ==========================================
# 3. SENTINELA INBOUND (SALES PLAYBOOK IA)
# ==========================================
def consultar_cerebro_playbook(cliente, mensagem_lead):
    playbook_objecoes = cliente.get('playbook_objecoes', [])
    agendamento = cliente.get('playbook_agendamento', {})
    
    prompt = f"""
    Você é o Executivo de Vendas da empresa '{cliente.get('nome_empresa')}'.
    Um lead acabou de te enviar esta mensagem no WhatsApp: "{mensagem_lead}"
    
    DIRETRIZES DO SEU CÉREBRO (PLAYBOOK):
    {json.dumps(playbook_objecoes, ensure_ascii=False)}
    
    REGRAS:
    1. Identifique se a mensagem do lead é uma objeção listada no playbook. Se for, use a resposta baseada nela, mas deixe natural.
    2. Se o lead demonstrar interesse real em avançar/conversar, você DEVE tentar agendar uma reunião.
       - A empresa permite agendamento? {'SIM' if agendamento.get('ativo') else 'NÃO'}
       - Link da agenda para enviar: {agendamento.get('link_agenda', 'Nenhum')}
    3. Responda de forma extremamente humana, curta e amigável, como se estivesse no WhatsApp.
    
    Retorne APENAS o texto da sua resposta. Nenhuma formatação extra.
    """
    try:
        resposta = client_ia.models.generate_content(
            model='gemini-2.5-flash', contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3)
        )
        return resposta.text.strip()
    except Exception as e:
        print(f"   ❌ Erro Gemini Playbook: {e}")
        return "Olá! Recebi sua mensagem. Tive um probleminha no meu sistema agora, mas já retorno para conversarmos melhor!"

def processar_respostas_whatsapp(page, cliente):
    print("\n   👀 [Sentinela IA] Verificando se algum lead respondeu no WhatsApp...")
    page.goto("https://web.whatsapp.com/")
    
    try:
        page.wait_for_selector('div[data-testid="chat-list"]', timeout=30000)
        time.sleep(5)
        
        chats_nao_lidos = page.locator('span[aria-label*="não lida"], span[aria-label*="unread"]').all()
        
        if not chats_nao_lidos:
            print("   ✅ Nenhuma mensagem nova no momento.")
            return

        print(f"   🚨 Encontradas {len(chats_nao_lidos)} conversas esperando resposta!")
        
        for chat in chats_nao_lidos:
            chat.click()
            time.sleep(3)
            
            mensagens_recebidas = page.locator('div.message-in span.selectable-text').all()
            if mensagens_recebidas:
                ultima_msg = mensagens_recebidas[-1].inner_text()
                print(f"   💬 Lead disse: '{ultima_msg[:50]}...'")
                
                print("   🧠 Pensando na melhor resposta para quebrar a objeção...")
                resposta_ia = consultar_cerebro_playbook(cliente, ultima_msg)
                
                print(f"   🤖 Respondendo: '{resposta_ia[:50]}...'")
                caixa_texto = page.wait_for_selector('div[title="Digite uma mensagem"], div[title="Type a message"]')
                caixa_texto.click()
                page.keyboard.type(resposta_ia, delay=50)
                time.sleep(1)
                page.locator('span[data-icon="send"]').first.click()
                time.sleep(3)
                
    except Exception as e:
        print(f"   ⚠️ Erro ao monitorar respostas: {e}")

# ==========================================
# 4. GERENCIADOR DE FROTA (ROUND ROBIN / ANTI-BAN)
# ==========================================
def obter_melhor_conta_remetente(cliente_id, plataforma):
    """
    Busca todas as contas ativas do cliente para a plataforma pedida.
    Retorna a conta que tem MENOS disparos hoje e que ainda não bateu o limite.
    """
    try:
        res = sb.table("contas_remetentes").select("*") \
            .eq("cliente_id", cliente_id) \
            .eq("plataforma", plataforma) \
            .eq("status", "ativo") \
            .execute()
        
        contas = res.data
        if not contas: return None
        
        contas_validas = [c for c in contas if c['disparos_hoje'] < c['limite_diario']]
        
        if not contas_validas:
            print(f"   ⚠️ [FROTA] Todos os chips de {plataforma} bateram o limite diário de segurança!")
            return None
            
        contas_ordenadas = sorted(contas_validas, key=lambda k: k['disparos_hoje'])
        return contas_ordenadas[0]
        
    except Exception as e:
        print(f"   ❌ Erro ao buscar frota: {e}")
        return None

def registrar_disparo_conta(conta_id, disparos_atuais):
    """Soma +1 no uso diário do chip para a barra de progresso no React."""
    try:
        sb.table("contas_remetentes").update({"disparos_hoje": disparos_atuais + 1}).eq("id", conta_id).execute()
    except Exception as e:
        pass


# ==========================================
# 5. MOTOR PRINCIPAL EXECUTOR
# ==========================================
def executar_tarefas(cliente_id):
    print("\n" + "="*50)
    print("🌾 INICIANDO AGENTE FARMER COM PLAYBOOK IA E VOZ")
    print("="*50)

    hoje = str(datetime.now().date())

    res_cli = sb.table("clientes").select("*").eq("id", cliente_id).execute()
    if not res_cli.data: return print("❌ Cliente não encontrado.")
    cliente = res_cli.data[0]
    
    res_leads = sb.table("leads_hunter").select("id").eq("cliente_id", cliente_id).execute()
    leads_ids = [l['id'] for l in res_leads.data]
    if not leads_ids: return print("❌ Nenhum lead.")

    # Busca Outbound (Disparos agendados)
    res_tarefas = sb.table("cadencia_agendada").select("*").in_("lead_id", leads_ids).lte("data_agendada", hoje).execute()
    tarefas = res_tarefas.data
    
    canais = cliente.get('canais_prospeccao', [])
    precisa_wpp = 'whatsapp' in canais
    precisa_lkdn = 'linkedin' in canais

    print("🚀 Iniciando Motor Playwright disfarçado...")
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR, 
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page_lkdn = browser.new_page() if precisa_lkdn else None
        page_wpp = browser.new_page() if precisa_wpp else None

        if page_wpp:
            print("   🟢 Carregando WhatsApp Web...")
            page_wpp.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=60000)
            
        if page_lkdn:
            print("   🔵 Carregando LinkedIn...")
            page_lkdn.goto("https://www.linkedin.com", wait_until="domcontentloaded", timeout=60000)

        if page_wpp or page_lkdn:
            time.sleep(15) # Pausa de Aquecimento

        # ----------------------------------------
        # FASE 1: EXECUÇÃO OUTBOUND (CADÊNCIA E UPSELL)
        # ----------------------------------------
        if tarefas:
            print(f"🔥 Executando {len(tarefas)} tarefas agendadas...")
            for tarefa in tarefas:
                acao = tarefa.get('tipo_acao')
                alvo = tarefa.get('contato_alvo')
                msg = tarefa.get('copy_mensagem', '')
                lead_id = tarefa.get('lead_id')

                print(f"\n▶️ Iniciando: [{acao.upper()}] - {tarefa.get('empresa_lead')}")
                sucesso = False

                if acao == 'email' and 'email' in canais:
                    sucesso = enviar_email_smtp(cliente, alvo, tarefa.get('assunto_email', 'Contato'), msg)

                # --- WHATSAPP (COM ROUND ROBIN E MULTI-CONTAS) ---
                elif acao == 'whatsapp' and page_wpp:
                    conta_wpp = obter_melhor_conta_remetente(cliente_id, 'whatsapp')
                    
                    if not conta_wpp:
                        print("   ⚠️ Pulando tarefa: Nenhum chip de WhatsApp disponível ou todos bateram o limite diário.")
                        sucesso = False
                    else:
                        print(f"   📱 Usando o chip: {conta_wpp['nome_perfil']} ({conta_wpp['disparos_hoje']}/{conta_wpp['limite_diario']} enviados hoje)")
                        
                        # Lógica de Áudio Clonado
                        voz_id = cliente.get('clonagem_voz_id')
                        if "[AUDIO]" in msg.upper() and voz_id:
                            msg_texto = msg.replace("[AUDIO]", "").replace("[audio]", "").strip()
                            caminho_audio = gerar_audio_dinamico(msg_texto, voz_id)
                            
                            if caminho_audio:
                                sucesso = enviar_audio_whatsapp(page_wpp, caminho_audio)
                                print("   ✅ Áudio clonado enviado com sucesso!")
                            else:
                                sucesso = enviar_whatsapp_humano(page_wpp, alvo, msg_texto)
                        else:
                            sucesso = enviar_whatsapp_humano(page_wpp, alvo, msg)

                        # Atualiza a barrinha de limite no banco
                        if sucesso:
                            registrar_disparo_conta(conta_wpp['id'], conta_wpp['disparos_hoje'])

                # --- UPSELL / PÓS-VENDA (TAMBÉM USA ROUND ROBIN) ---
                elif acao == 'pos_venda' and page_wpp:
                    print("   💸 Disparando mensagem de UPSell / Pós-Venda!")
                    conta_wpp = obter_melhor_conta_remetente(cliente_id, 'whatsapp')
                    
                    if not conta_wpp:
                        print("   ⚠️ Pulando Upsell: Nenhum chip de WhatsApp disponível.")
                        sucesso = False
                    else:
                        print(f"   📱 Usando o chip: {conta_wpp['nome_perfil']}")
                        sucesso = enviar_whatsapp_humano(page_wpp, alvo, msg)
                        
                        if sucesso:
                            registrar_disparo_conta(conta_wpp['id'], conta_wpp['disparos_hoje'])

                elif acao in ['visitar', 'curtir', 'conectar'] and page_lkdn:
                    try:
                        page_lkdn.goto(alvo)
                        time.sleep(random.uniform(4.0, 7.0))
                        if acao == 'visitar': sucesso = True
                        elif acao == 'curtir':
                            page_lkdn.mouse.wheel(0, 500); time.sleep(2); sucesso = True
                        elif acao == 'conectar':
                            btn = page_lkdn.locator("button:has-text('Conectar'), button:has-text('Connect')").first
                            if btn.is_visible(): 
                                btn.click(); time.sleep(1)
                                page_lkdn.locator("button:has-text('Adicionar nota')").click()
                                page_lkdn.fill("textarea[name='message']", msg)
                                time.sleep(1)
                                page_lkdn.locator("button:has-text('Enviar')").first.click()
                                sucesso = True
                    except Exception as e:
                        print(f"   ❌ Erro LinkedIn: {e}")

                elif acao == 'remarketing':
                    sucesso = True

                # FINALIZA A TAREFA E ATUALIZA CRM
                if sucesso:
                    sb.table("cadencia_agendada").delete().eq("id", tarefa['id']).execute()
                    
                    if acao not in ['remarketing', 'pos_venda']:
                        novo_status = {"visitar": "👀 LinkedIn Visitado", "conectar": "💬 Contato Feito", "email": "💬 Contato Feito", "whatsapp": "💬 Contato Feito"}.get(acao, "🎯 Prospecção")
                        sb.table("leads_hunter").update({"status_funil": novo_status}).eq("id", lead_id).execute()
                    
                    time.sleep(random.randint(15, 45))

        # ----------------------------------------
        # FASE 2: INBOUND (QUEBRA DE OBJEÇÕES E CONCIERGE)
        # ----------------------------------------
        if page_wpp:
            processar_respostas_whatsapp(page_wpp, cliente)

        browser.close()
        print("\n🏁 EXPEDIENTE FINALIZADO COM SUCESSO!")

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) > 1:
        executar_tarefas(sys.argv[1])
    else:
        print("⚠️ ERRO: O ID do cliente não foi fornecido.")