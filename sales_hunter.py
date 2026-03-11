import os
import json
import time
import requests
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
from google import genai
from google.genai import types
from supabase import create_client, Client

load_dotenv()

# --- CREDENCIAIS ---
API_KEY = os.getenv("TRELLO_API_KEY")
API_TOKEN = os.getenv("TRELLO_API_TOKEN")
BOARD_ID = os.getenv("TRELLO_BOARD_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inicializando Clientes (Google e Supabase)
client = genai.Client(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

CIDADE_ALVO = "Araçatuba, SP"
ESTRATEGIA_NICHOS = {
    "Clínicas Odontológicas e Estética": "Necessidade de consórcio para equipamentos e maquininha com taxa justa.",
    "Agronegócio e Lojas de Insumos": "Linhas de custeio e agilidade na liberação de crédito rural.",
    "Supermercados e Distribuidoras": "Redução drástica do custo da folha de pagamento e taxas de Pix/Boletos.",
    "Transportadoras e Logística": "Consórcio de veículos pesados e seguro de frota."
}

# --- FUNÇÕES DO SUPABASE ---
def salvar_lead_supabase(dados_lead):
    # Insere o novo lead na tabela principal e retorna o ID (UUID)
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
        return response.data[0]['id'] # Retorna o UUID gerado
    except Exception as e:
        print(f"Erro ao salvar no Supabase: {e}")
        return None

def registrar_interacao_supabase(lead_id, mensagem, status_funil):
    # Atualiza o status do lead
    supabase.table("leads_hunter").update({"status_funil": status_funil}).eq("id", lead_id).execute()
    # Registra a copy enviada no histórico
    interacao = {
        "lead_id": lead_id,
        "canal": "whatsapp_script",
        "mensagem_enviada": mensagem
    }
    supabase.table("interacoes").insert(interacao).execute()

# --- FUNÇÕES DO TRELLO ---
def obter_listas_trello():
    url = f"https://api.trello.com/1/boards/{BOARD_ID}/lists"
    resp = requests.get(url, params={'key': API_KEY, 'token': API_TOKEN})
    return {lista['name']: lista['id'] for lista in resp.json()} if resp.status_code == 200 else {}

def obter_cards_da_lista(id_lista):
    url = f"https://api.trello.com/1/lists/{id_lista}/cards"
    resp = requests.get(url, params={'key': API_KEY, 'token': API_TOKEN})
    return resp.json() if resp.status_code == 200 else []

def mover_card(id_card, id_nova_lista):
    url = f"https://api.trello.com/1/cards/{id_card}"
    requests.put(url, params={'key': API_KEY, 'token': API_TOKEN, 'idList': id_nova_lista})

def atualizar_descricao_card(id_card, nova_descricao):
    url = f"https://api.trello.com/1/cards/{id_card}"
    requests.put(url, params={'key': API_KEY, 'token': API_TOKEN, 'desc': nova_descricao})

def criar_card_lead(id_lista, dados_lead, lead_id_db):
    url = "https://api.trello.com/1/cards"
    descricao = (
        f"**📍 Localização:** {dados_lead.get('cidade', CIDADE_ALVO)}\n"
        f"**👤 Sócio/Contato:** {dados_lead.get('nome_socio', 'Buscar no sistema')}\n"
        f"**🌐 Redes:** {dados_lead.get('links_encontrados', 'Não informado')}\n\n"
        f"**🚨 Dor Focada:** {dados_lead.get('dor_presumida', '')}\n"
        f"**🎣 Gancho:** {dados_lead.get('hobbies_ou_interesses', '')}\n\n"
        f"---\n**📝 Copy Inicial:**\n{dados_lead.get('copy_persuasiva', '')}\n\n"
        f"---\n**ID_DB:** {lead_id_db}" # <-- O Elo de ligação com o Supabase
    )
    requests.post(url, params={
        'idList': id_lista, 'key': API_KEY, 'token': API_TOKEN,
        'name': f"🏢 {dados_lead.get('nome_empresa', 'Empresa')} - {dados_lead.get('nicho', '')}",
        'desc': descricao, 'pos': 'bottom'
    })

# --- MOTORES DE INTELIGÊNCIA (GEMINI) ---
def buscar_lote_de_leads(nicho, dor, quantidade=10):
    print(f"🕵️‍♂️ Mapeando empresas do nicho: {nicho}...")
    prompt = f"""
    Faça uma busca web real e encontre {quantidade} empresas diferentes do nicho de '{nicho}' ativas na cidade de '{CIDADE_ALVO}'.
    A dor que o Sicredi (Cooperativa) vai atacar é: {dor}.
    Para CADA empresa, descubra o nome, tente achar o nome de um sócio, e identifique um gancho em redes sociais.
    Crie uma copy curta e muito amigável para WhatsApp para agendar um café.
    Retorne ESTRITAMENTE um array JSON contendo {quantidade} objetos com as chaves:
    "nome_empresa", "nome_socio", "nicho", "cidade", "links_encontrados", "dor_presumida", "hobbies_ou_interesses", "copy_persuasiva"
    """
    try:
        resposta = client.models.generate_content(
            model='gemini-2.5-flash', contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}], response_mime_type="application/json", temperature=0.5
            )
        )
        return json.loads(resposta.text)
    except Exception as e:
        print(f"Erro ao buscar lote para {nicho}: {e}")
        return []

def gerar_copy_remarketing(nome_empresa, nivel_remarketing):
    prompt = f"Gere uma mensagem curta de WhatsApp de Remarketing ({nivel_remarketing}) para a empresa {nome_empresa}. Aja como gerente do Sicredi. Seja educado, não incomode, ofereça um café rápido para ajudar o negócio. Retorne APENAS o texto."
    try:
        resposta = client.models.generate_content(
            model='gemini-2.5-flash', contents=prompt,
            config=types.GenerateContentConfig(temperature=0.7)
        )
        return resposta.text.strip()
    except:
        return "Olá, tentamos contato anteriormente. Gostaria de tomar um café de 10 minutos esta semana para apresentar os diferenciais da nossa cooperativa?"

# --- LÓGICA DE GESTÃO DO FUNIL ---
def processar_remarketing_e_geladeira(listas_trello):
    hoje = datetime.now(timezone.utc)
    fluxo = [
        ("Prospecção", "Remarketing 1", 15),
        ("Remarketing 1", "Remarketing 2", 15),
        ("Remarketing 2", "Remarketing 3", 15),
        ("Remarketing 3", "Remarketing 4", 15),
        ("Respondeu Não", "Prospecção", 90)
    ]
    
    for lista_origem, lista_destino, dias_limite in fluxo:
        if lista_origem not in listas_trello or lista_destino not in listas_trello:
            continue
            
        cards = obter_cards_da_lista(listas_trello[lista_origem])
        for card in cards:
            data_movimento = datetime.strptime(card['dateLastActivity'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            dias_parado = (hoje - data_movimento).days
            
            if dias_parado >= dias_limite:
                print(f"🔄 Movendo {card['name']} para '{lista_destino}'...")
                
                # Gera nova copy
                nivel_rmk = lista_destino if "Remarketing" in lista_destino else "Reconquista"
                nova_copy = gerar_copy_remarketing(card['name'], nivel_rmk)
                nova_desc = card['desc'] + f"\n\n---\n**📝 Nova Copy ({nivel_rmk}):**\n{nova_copy}"
                
                # Extrai o ID do Supabase do Trello e grava no banco de dados
                if "**ID_DB:**" in card['desc']:
                    lead_id = card['desc'].split("**ID_DB:**")[1].strip()
                    registrar_interacao_supabase(lead_id, nova_copy, status_funil=lista_destino)
                
                atualizar_descricao_card(card['id'], nova_desc)
                mover_card(card['id'], listas_trello[lista_destino])
                time.sleep(2)

def gerar_planilha_leads_quentes(listas_trello):
    if "Respondeu Ok" not in listas_trello: return
    cards_ok = obter_cards_da_lista(listas_trello["Respondeu Ok"])
    dados_excel = [{"Empresa/Lead": c['name'], "Resumo": c['desc'], "Link Trello": c['shortUrl']} for c in cards_ok]
    if dados_excel:
        pd.DataFrame(dados_excel).to_excel("leads_quentes_sicredi.xlsx", index=False)
        print("📊 Planilha 'leads_quentes_sicredi.xlsx' atualizada!")

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    print("🚀 Iniciando Motor Hunter IA + Supabase...")
    listas = obter_listas_trello()
    
    if not listas:
        print("❌ Erro ao ler Trello.")
        exit()

    print("🧹 Analisando follow-ups e cards antigos...")
    processar_remarketing_e_geladeira(listas)
    
    gerar_planilha_leads_quentes(listas)
    
    if "Prospecção" in listas:
        print("🎯 Iniciando caçada pelos 40 leads da semana...")
        for nicho, dor in ESTRATEGIA_NICHOS.items():
            leads_nicho = buscar_lote_de_leads(nicho, dor, quantidade=10)
            for lead in leads_nicho:
                # 1. Salva no Banco de Dados e pega o UUID
                id_db = salvar_lead_supabase(lead)
                
                # 2. Registra a primeira Copy no histórico do banco
                if id_db:
                    registrar_interacao_supabase(id_db, lead.get('copy_persuasiva', ''), "Prospecção")
                
                # 3. Cria no Trello com a Tag de identificação do Banco
                criar_card_lead(listas["Prospecção"], lead, id_db)
            
            print(f"✅ 10 leads de '{nicho}' injetados. Pausando 15s...")
            time.sleep(15) 
    
    print("🏁 Execução da semana concluída.")