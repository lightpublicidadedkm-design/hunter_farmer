import os
import json
import time
import re
import urllib.parse
import pandas as pd
import schedule
from datetime import datetime, timezone
from dotenv import load_dotenv
from google import genai
from google.genai import types
from supabase import create_client, Client
from playwright.sync_api import sync_playwright

load_dotenv()

# ==========================================
# 1. CONFIGURAÇÕES E CREDENCIAIS
# ==========================================
API_KEY = os.getenv("TRELLO_API_KEY")
API_TOKEN = os.getenv("TRELLO_API_TOKEN")
BOARD_ID = os.getenv("TRELLO_BOARD_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

PROFILE_DIR = "./whatsapp_session"
CIDADE_ALVO = "Araçatuba, SP"
ESTRATEGIA_NICHOS = {
    "Clínicas Odontológicas e Estética": "Alto custo de consórcio para equipamentos e taxas abusivas de maquininha que corroem o lucro.",
    "Agronegócio e Lojas de Insumos": "Burocracia e lentidão na liberação de linhas de custeio e crédito rural nos bancos tradicionais.",
    "Supermercados e Distribuidoras": "Margens espremidas devido ao alto custo da folha de pagamento e taxas elevadas de Pix e Boletos.",
    "Transportadoras e Logística": "Dificuldade e custo alto para renovação de frota (caminhões) e seguros."
}

# ==========================================
# 2. INTEGRAÇÃO SUPABASE (CRM BIDIRECIONAL)
# ==========================================
def salvar_lead_supabase(dados_lead):
    data = {
        "nome_empresa": dados_lead.get("nome_empresa", "Não informado"),
        "nicho_mercado": dados_lead.get("nicho", ""),
        "nome_socio": dados_lead.get("nome_socio", "Não encontrado"),
        "links_redes_sociais": {"links": dados_lead.get("links_encontrados", "")},
        "dor_presumida": dados_lead.get("dor_presumida", ""),
        "hobbies_interesses": dados_lead.get("hobbies_ou_interesses", ""),
        "status_funil": "Prospecção"
    }
    try:
        response = supabase.table("leads_hunter").insert(data).execute()
        return response.data[0]['id'] 
    except Exception as e:
        print(f"❌ [DB] Erro ao salvar lead no Supabase: {e}")
        return None

def registrar_interacao_supabase(lead_id, status_funil, canal="WhatsApp Bot", mensagem_enviada=None, resposta_lead=None, proximo_passo=None):
    if not lead_id: return
    try:
        supabase.table("leads_hunter").update({"status_funil": status_funil}).eq("id", lead_id).execute()
        interacao = {
            "lead_id": lead_id,
            "canal": canal,
            "mensagem_enviada": mensagem_enviada,
            "resposta_lead": resposta_lead,
            "proximo_passo_recomendado": proximo_passo
        }
        supabase.table("interacoes").insert(interacao).execute()
    except Exception as e:
        print(f"❌ [DB] Erro ao gravar interação: {e}")


# ==========================================
# 3. INTEGRAÇÃO TRELLO
# ==========================================
def obter_listas_trello():
    resp = requests.get(f"https://api.trello.com/1/boards/{BOARD_ID}/lists", params={'key': API_KEY, 'token': API_TOKEN})
    return {lista['name']: lista['id'] for lista in resp.json()} if resp.status_code == 200 else {}

def obter_cards_da_lista(id_lista):
    resp = requests.get(f"https://api.trello.com/1/lists/{id_lista}/cards", params={'key': API_KEY, 'token': API_TOKEN})
    return resp.json() if resp.status_code == 200 else []

def atualizar_card_trello(id_card, id_nova_lista=None, nova_descricao=None):
    params = {'key': API_KEY, 'token': API_TOKEN}
    if id_nova_lista: params['idList'] = id_nova_lista
    if nova_descricao: params['desc'] = nova_descricao
    requests.put(f"https://api.trello.com/1/cards/{id_card}", params=params)

def criar_card_lead(id_lista, dados_lead, lead_id_db):
    desc = (
        f"**📍 Localização:** {dados_lead.get('cidade', CIDADE_ALVO)}\n"
        f"**👤 Sócio/Contato:** {dados_lead.get('nome_socio', 'Buscar no sistema')}\n"
        f"**📱 WhatsApp:** {dados_lead.get('telefone_whatsapp', 'N/A')}\n"
        f"**🌐 Redes:** {dados_lead.get('links_encontrados', 'Não informado')}\n\n"
        f"**🚨 Dor Focada:** {dados_lead.get('dor_presumida', '')}\n"
        f"**🎣 Gancho:** {dados_lead.get('hobbies_ou_interesses', '')}\n\n"
        f"---\n**📝 Copy Inicial:**\n{dados_lead.get('copy_persuasiva', '')}\n\n"
        f"---\n**ID_DB:** {lead_id_db}\n"
        f"**📅 Último Envio:** " 
    )
    requests.post("https://api.trello.com/1/cards", params={
        'idList': id_lista, 'key': API_KEY, 'token': API_TOKEN,
        'name': f"🏢 {dados_lead.get('nome_empresa', 'Empresa')} - {dados_lead.get('nicho', '')}",
        'desc': desc, 'pos': 'bottom'
    })

def extrair_dados_card(desc):
    telefone = re.search(r'\*\*📱 WhatsApp:\*\* (.*?)\n', desc)
    data_envio = re.search(r'\*\*📅 Último Envio:\*\* (.*?)$', desc, re.MULTILINE)
    id_db = re.search(r'\*\*ID_DB:\*\* (.*?)\n', desc)
    
    copy = None
    if "**📝 Copy" in desc:
        partes = desc.split("**📝 Copy")
        copy_bruta = partes[-1].split("---")[0].strip()
        if ":" in copy_bruta[:15]: copy = copy_bruta.split(":", 1)[1].strip()
        else: copy = copy_bruta
    
    return {
        "telefone": telefone.group(1).strip() if telefone else None,
        "data_envio": data_envio.group(1).strip() if data_envio and data_envio.group(1).strip() else None,
        "id_db": id_db.group(1).strip() if id_db else None,
        "copy": copy
    }


# ==========================================
# 4. INTELIGÊNCIA ARTIFICIAL (GEMINI PERSUASÃO)
# ==========================================
def buscar_lote_de_leads(nicho, dor, quantidade=10):
    print(f"🕵️‍♂️ [IA] Mapeando empresas e formulando copys (Dale Carnegie + PAS) para: {nicho}...")
    prompt = f"""
    Encontre {quantidade} empresas diferentes do nicho de '{nicho}' ativas na cidade de '{CIDADE_ALVO}'.
    Aja como Especialista em Vendas B2B do Sicredi. A dor do mercado é: "{dor}".
    
    Para CADA empresa ache: Nome, Nome do Sócio, WhatsApp público (formato 5518999999999) e Gancho em redes.
    Se não achar o telefone, retorne "N/A".
    
    Crie a copy para WhatsApp com estas técnicas:
    1. Nome do dono (ou equipe) na primeira linha.
    2. Elogie o gancho real que encontrou.
    3. PAS: Fale que você ajuda o setor de {nicho} com [a dor].
    4. Soft Ask: "Faz sentido batermos um papo rápido sobre isso essa semana, ou o momento não é o ideal?"
    Curta, sem jargão bancário pesado, humana.
    
    Retorne ESTRITAMENTE um array JSON contendo as chaves:
    "nome_empresa", "nome_socio", "telefone_whatsapp", "nicho", "cidade", "links_encontrados", "dor_presumida", "hobbies_ou_interesses", "copy_persuasiva".
    Não use markdown de bloco de código. Comece com [ e termine com ].
    """
    try:
        resposta = client.models.generate_content(
            model='gemini-2.5-flash', contents=prompt,
            config=types.GenerateContentConfig(tools=[{"google_search": {}}], temperature=0.7)
        )
        texto_limpo = resposta.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(texto_limpo)
    except Exception as e:
        print(f"❌ [IA] Erro ao buscar lote para {nicho}: {e}")
        return []

def analisar_resposta_e_gerar_passo(mensagem_cliente):
    prompt = f"""
    Analise esta resposta de um lead B2B no WhatsApp: "{mensagem_cliente}".
    1. Status: O cliente foi receptivo/quer conversar ("OK") ou dispensou ("NÃO")?
    2. Próximo Passo: Escreva uma breve recomendação comercial de como a agência deve responder a ele agora.
    
    Retorne APENAS um JSON: {{"status": "OK ou NÃO", "recomendacao": "sua sugestao aqui"}}
    """
    try:
        resposta = client.models.generate_content(
            model='gemini-2.5-flash', contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json")
        )
        return json.loads(resposta.text)
    except:
        return {"status": "OK", "recomendacao": "Analisar manualmente e dar andamento."}

def gerar_copy_remarketing(nome_empresa, nivel_remarketing):
    instrucoes = {
        "Remarketing 1": "Técnica do 'Bump'. Super curta. Ex: 'Oi, sei que a rotina é corrida, só passando para ver se conseguiu dar uma olhada na mensagem acima.'",
        "Remarketing 2": "9-Word Email. Pergunta direta sem rodeios. Ex: 'Oi [Nome], você ainda tem interesse em reduzir as taxas da maquininha da [Empresa]?'",
        "Remarketing 3": "Prova Social Local. Fale que ajudou um parceiro do setor recentemente.",
        "Remarketing 4": "Breakup Message. Gatilho de perda. Ex: 'Como não tive retorno, imagino que já estejam bem resolvidos nisso. Vou parar de insistir, mas deixo meu contato. Abraço!'"
    }
    
    prompt = f"Aja como Executivo de Contas B2B do Sicredi falando com a empresa {nome_empresa}. Use a seguinte técnica para o nível {nivel_remarketing}: {instrucoes.get(nivel_remarketing)}. Retorne APENAS o texto exato da mensagem."
    
    try:
        resp = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return resp.text.strip()
    except:
        return f"Olá! Deixamos nosso papo em stand-by. Faz sentido retomarmos a conversa sobre a {nome_empresa} esta semana?"


# ==========================================
# 5. AUTOMAÇÃO RPA (PLAYWRIGHT / WHATSAPP WEB)
# ==========================================
def horario_permitido():
    """Retorna True se estiver entre 08:00 e 16:59"""
    hora_atual = datetime.now().hour
    return 8 <= hora_atual < 17

def enviar_mensagem_whatsapp(page, telefone, mensagem):
    telefone_limpo = ''.join(filter(str.isdigit, str(telefone)))
    if not telefone_limpo.startswith("55"): telefone_limpo = f"55{telefone_limpo}"
    
    texto_codificado = urllib.parse.quote(mensagem)
    link_envio = f"https://web.whatsapp.com/send?phone={telefone_limpo}&text={texto_codificado}"
    
    print(f"   [RPA] Acessando chat de {telefone_limpo}...")
    page.goto(link_envio)
    
    try:
        botao_enviar = page.wait_for_selector('span[data-icon="send"]', timeout=25000)
        time.sleep(2) 
        botao_enviar.click()
        time.sleep(3) 
        print(f"   ✅ [RPA] Mensagem disparada!")
        return True
    except Exception as e:
        print(f"   ❌ [RPA] Falha ao enviar para {telefone}. Número inválido ou erro de carregamento.")
        return False

def monitorar_respostas_inbound(page, listas_trello):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 👀 [RPA] Vasculhando novas mensagens...")
    page.goto("https://web.whatsapp.com/")
    
    try:
        page.wait_for_selector('div[data-testid="chat-list"]', timeout=30000)
        time.sleep(5)
        
        chats_nao_lidos = page.locator('span[aria-label*="não lida"], span[aria-label*="unread"]').all()
        
        if not chats_nao_lidos: return
        print(f"   🔔 Encontradas {len(chats_nao_lidos)} conversas com resposta!")
        
        for chat_icon in chats_nao_lidos:
            chat_icon.click()
            time.sleep(3)
            
            cabecalho = page.locator('header').inner_text()
            telefone_chat = ''.join(filter(str.isdigit, cabecalho))
            
            mensagens_recebidas = page.locator('div.message-in span.selectable-text').all()
            if mensagens_recebidas:
                ultima_msg = mensagens_recebidas[-1].inner_text()
                print(f"   💬 Cliente enviou: {ultima_msg[:40]}...")
                
                analise = analisar_resposta_e_gerar_passo(ultima_msg)
                lista_destino = "Respondeu Ok" if analise["status"] == "OK" else "Respondeu Não"
                print(f"   🧠 [IA] Classificou: {lista_destino}")
                
                dados_card = mover_card_por_telefone(telefone_chat, listas_trello[lista_destino])
                if dados_card and dados_card['id_db']:
                    registrar_interacao_supabase(
                        lead_id=dados_card['id_db'], 
                        status_funil=lista_destino,
                        canal="WhatsApp Inbound",
                        resposta_lead=ultima_msg,
                        proximo_passo=analise["recomendacao"]
                    )
            time.sleep(2)
    except Exception as e:
        print(f"   ⚠️ [RPA] Erro leve no monitoramento: {e}")

def mover_card_por_telefone(telefone_procurado, id_lista_destino):
    listas = obter_listas_trello()
    listas_busca = ["Prospecção", "Remarketing 1", "Remarketing 2", "Remarketing 3", "Remarketing 4"]
    
    for nome_lista in listas_busca:
        if nome_lista in listas:
            for card in obter_cards_da_lista(listas[nome_lista]):
                dados = extrair_dados_card(card['desc'])
                if dados['telefone']:
                    tel_card = ''.join(filter(str.isdigit, dados['telefone']))
                    if telefone_procurado in tel_card or tel_card in telefone_procurado:
                        atualizar_card_trello(card['id'], id_nova_lista=id_lista_destino)
                        return dados
    return None


# ==========================================
# 6. ENGENHARIA DO FLUXO DO MOTOR (LOOPS)
# ==========================================
def motor_disparo_inicial(page):
    print("\n🚀 [FLUXO] Buscando novos leads para disparar no WhatsApp...")
    
    # --- TRAVA DE HORÁRIO COMERCIAL ---
    if not horario_permitido():
        print("   ⏳ Fora do horário comercial (08:00 - 17:00). Pausando envios por enquanto.")
        return

    listas = obter_listas_trello()
    if "Prospecção" not in listas: return
    
    for card in obter_cards_da_lista(listas["Prospecção"]):
        # Checa novamente o horário a cada loop (caso o processo dure horas)
        if not horario_permitido():
            print("   ⏳ Deu o horário limite (17h). Interrompendo envios restantes para amanhã.")
            break

        dados = extrair_dados_card(card['desc'])
        
        if dados['telefone'] and dados['telefone'] != "N/A" and dados['copy'] and not dados['data_envio']:
            sucesso = enviar_mensagem_whatsapp(page, dados['telefone'], dados['copy'])
            
            if sucesso:
                hoje = datetime.now().strftime("%Y-%m-%d")
                nova_desc = card['desc'].replace("**📅 Último Envio:** ", f"**📅 Último Envio:** {hoje}")
                atualizar_card_trello(card['id'], nova_descricao=nova_desc)
                
                if dados['id_db']:
                    registrar_interacao_supabase(dados['id_db'], "Prospecção", "WhatsApp Outbound", dados['copy'])
                
                print("   🛡️ Escudo Anti-Ban: Pausa de 3 minutos...")
                time.sleep(180) 

def motor_remarketing_automatico(page):
    print("\n🔄 [FLUXO] Varrendo funil de Remarketing...")
    
    # --- TRAVA DE HORÁRIO COMERCIAL ---
    if not horario_permitido():
        print("   ⏳ Fora do horário comercial (08:00 - 17:00). Pausando remarketing.")
        return

    listas = obter_listas_trello()
    hoje = datetime.now()
    
    fluxos = [
        ("Prospecção", "Remarketing 1", 15),
        ("Remarketing 1", "Remarketing 2", 15),
        ("Remarketing 2", "Remarketing 3", 15),
        ("Remarketing 3", "Remarketing 4", 15),
        ("Respondeu Não", "Prospecção", 90) 
    ]
    
    for origem, destino, dias_espera in fluxos:
        if origem not in listas or destino not in listas: continue
        
        for card in obter_cards_da_lista(listas[origem]):
            # Checa horário dentro do loop
            if not horario_permitido():
                print("   ⏳ Deu o horário limite (17h). Interrompendo remarketing.")
                return

            dados = extrair_dados_card(card['desc'])
            
            if dados['data_envio']:
                try:
                    data_ultimo_envio = datetime.strptime(dados['data_envio'], "%Y-%m-%d")
                    dias_passados = (hoje - data_ultimo_envio).days
                    
                    if dias_passados >= dias_espera:
                        print(f"   ⏰ Tempo atingido para {card['name']}. Escalonando para {destino}...")
                        
                        nova_copy = gerar_copy_remarketing(card['name'], destino)
                        sucesso = enviar_mensagem_whatsapp(page, dados['telefone'], nova_copy)
                        
                        if sucesso:
                            nova_desc = card['desc'].replace(dados['data_envio'], hoje.strftime("%Y-%m-%d"))
                            nova_desc += f"\n\n---\n**📝 Copy Inicial ({destino}):**\n{nova_copy}"
                            atualizar_card_trello(card['id'], id_nova_lista=listas[destino], nova_descricao=nova_desc)
                            
                            if dados['id_db']:
                                registrar_interacao_supabase(dados['id_db'], destino, "WhatsApp Outbound", nova_copy)
                                
                            print("   🛡️ Escudo Anti-Ban: Pausa de 3 minutos...")
                            time.sleep(180)
                except Exception as e:
                    print(f"Erro ao calcular datas do card {card['name']}: {e}")

def executar_rotina_hunter():
    print("\n🎯 [FLUXO] Iniciando caçada semanal (Google -> Trello -> Supabase)...")
    listas = obter_listas_trello()
    
    for nicho, dor in ESTRATEGIA_NICHOS.items():
        leads = buscar_lote_de_leads(nicho, dor, 10)
        for lead in leads:
            id_db = salvar_lead_supabase(lead)
            if id_db:
                registrar_interacao_supabase(id_db, "Prospecção", "Criação de Copy", lead.get('copy_persuasiva', ''))
                criar_card_lead(listas["Prospecção"], lead, id_db)
        print(f"✅ Leads de '{nicho}' na base. Pausa de 10s...")
        time.sleep(10)


# ==========================================
# 7. INICIALIZAÇÃO INFINITA (AGENDADOR E BROWSER)
# ==========================================
def iniciar_robo_local():
    print("🤖 Ligando Agente Master e Inicializando Navegador...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(user_data_dir=PROFILE_DIR, headless=False)
        page = browser.new_page()
        
        print("🌐 Acessando WhatsApp. Se for o 1º acesso, leia o QR Code com o celular de prospecção.")
        page.goto("https://web.whatsapp.com/")
        
        try:
            page.wait_for_selector('div[data-testid="chat-list"]', timeout=60000)
            print("✅ Conectado ao WhatsApp com sucesso!")
        except:
            print("⚠️ Tempo de QR Code expirado. O robô tentará conectar novamente.")

        listas_trello = obter_listas_trello()
        
        # Agendamentos principais
        schedule.every(10).minutes.do(monitorar_respostas_inbound, page=page, listas_trello=listas_trello)
        schedule.every(30).minutes.do(motor_disparo_inicial, page=page)
        schedule.every().day.at("10:00").do(motor_remarketing_automatico, page=page)
        schedule.every().monday.at("08:00").do(executar_rotina_hunter)
        
        print("\n🟢 SISTEMA DE VENDAS 100% ONLINE E AUTÔNOMO.")
        print("💡 Deixe este terminal aberto. As regras de Horário Comercial (08h às 17h) estão ativas.")
        
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    iniciar_robo_local()