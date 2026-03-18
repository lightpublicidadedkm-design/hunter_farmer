import os
import json
import time
import urllib.parse # <-- Importação que causou o erro na imagem corrigida
import pandas as pd
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google import genai
from google.genai import types
from supabase import create_client, Client
import time

load_dotenv()

def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

# --- CREDENCIAIS MESTRE (SERVER-SIDE) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client_ia = genai.Client(api_key=GEMINI_API_KEY)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# INTEGRAÇÃO SUPABASE & TRELLO
# ==========================================
def verificar_lead_existente(nome_empresa):
    try:
        resp = supabase.table("leads_hunter").select("id").ilike("nome_empresa", f"%{nome_empresa}%").execute()
        return len(resp.data) > 0
    except:
        return False

def salvar_lead_supabase(lead, cliente_id):
    data = {
        "cliente_id": cliente_id,
        "nome_empresa": lead.get("nome_empresa", "Não informado"),
        "nicho_mercado": lead.get("nicho", ""),
        "nome_socio": lead.get("nome_socio", "Não encontrado"),
        "dor_presumida": lead.get("dor_identificada_para_o_produto", "Não encontrada"),
        "status_funil": "Prospecção",
        "endereco": lead.get("endereco", "Não informado"),
        "email": lead.get("email_adivinhado", "Não informado"),
        "telefone_fixo": lead.get("telefone_fixo", "N/A"),
        "links_redes_sociais": {
            "site": lead.get("site_empresa", ""),
            "linkedin_empresa": lead.get("linkedin_empresa", ""),
            "linkedin_decisor": lead.get("linkedin_decisor", ""),
            "linkedin_cto": lead.get("linkedin_cto", "")
        }
    }
    try:
        response = supabase.table("leads_hunter").insert(data).execute()
        return response.data[0]['id'] 
    except:
        return None

def agendar_cadencia_supabase(lead_id, lead):
    """Calcula as datas e salva a linha do tempo exata na tabela cadencia_agendada."""
    if not lead_id: return
    
    hoje = datetime.now().date()
    linkedin_url = lead.get("linkedin_decisor", "")
    email_url = lead.get("email_adivinhado", "")
    empresa = lead.get("nome_empresa", "Empresa N/A")
    
    if linkedin_url == "Não encontrado" or not linkedin_url:
        linkedin_url = lead.get("linkedin_empresa", "") 
        
    tarefas = []

    # [D0] Visitar | [D2] Curtir | [D3] E-mail | [D15] Conexão | [D30] Inbox 1 | [6M] Inbox 2
    if linkedin_url and linkedin_url != "Não encontrado":
        tarefas.append({"lead_id": lead_id, "empresa_lead": empresa, "tipo_acao": "visitar", "plataforma": "LinkedIn", "data_agendada": str(hoje), "contato_alvo": linkedin_url})
        tarefas.append({"lead_id": lead_id, "empresa_lead": empresa, "tipo_acao": "curtir", "plataforma": "LinkedIn", "data_agendada": str(hoje + timedelta(days=2)), "contato_alvo": linkedin_url})
        tarefas.append({"lead_id": lead_id, "empresa_lead": empresa, "tipo_acao": "conectar", "plataforma": "LinkedIn", "data_agendada": str(hoje + timedelta(days=15)), "contato_alvo": linkedin_url, "copy_mensagem": lead.get("linkedin_nota_conexao", "")})
        tarefas.append({"lead_id": lead_id, "empresa_lead": empresa, "tipo_acao": "mensagem", "plataforma": "LinkedIn", "data_agendada": str(hoje + timedelta(days=30)), "contato_alvo": linkedin_url, "copy_mensagem": lead.get("linkedin_inbox_1", "")})
        tarefas.append({"lead_id": lead_id, "empresa_lead": empresa, "tipo_acao": "mensagem", "plataforma": "LinkedIn", "data_agendada": str(hoje + timedelta(days=180)), "contato_alvo": linkedin_url, "copy_mensagem": lead.get("linkedin_inbox_2", "")})

    if email_url and email_url != "Não encontrado":
        tarefas.append({"lead_id": lead_id, "empresa_lead": empresa, "tipo_acao": "email", "plataforma": "Email", "data_agendada": str(hoje + timedelta(days=3)), "contato_alvo": email_url, "assunto_email": lead.get("email_assunto", ""), "copy_mensagem": lead.get("email_corpo", "")})

    try:
        if tarefas:
            supabase.table("cadencia_agendada").insert(tarefas).execute()
    except Exception as e:
        print(f"   ⚠️ Erro ao agendar cadência: {e}")

def criar_card_trello(cliente, lead, id_db):
    """Cria card no Trello usando as credenciais específicas do cliente do banco."""
    key = cliente.get('trello_api_key')
    token = cliente.get('trello_token')
    board_id = cliente.get('trello_board_id')
    
    if not key or not token or not board_id: return

    try:
        resp = requests.get(f"https://api.trello.com/1/boards/{board_id}/lists", params={'key': key, 'token': token})
        listas = {lista['name']: lista['id'] for lista in resp.json()}
        id_lista = listas.get("Prospecção")
        
        if id_lista:
            data_hoje = datetime.now()
            desc = (
                f"**👤 Decisor:** {lead.get('nome_socio', '')}\n"
                f"**📧 E-mail:** {lead.get('email_adivinhado', 'N/A')}\n"
                f"**🔗 LinkedIn:** {lead.get('linkedin_decisor', 'N/A')}\n\n"
                f"**🎯 Dor Detectada (Google/RA):** {lead.get('dor_identificada_para_o_produto', 'N/A')}\n"
                f"---\n### 📅 CHECKLIST ABM\n"
                f"[ ] D0: Visitar Perfil | [ ] D2: Curtir | [ ] D3: E-mail"
            )
            requests.post("https://api.trello.com/1/cards", params={
                'idList': id_lista, 'key': key, 'token': token,
                'name': f"🏢 {lead.get('nome_empresa', 'Empresa')} - {lead.get('nicho', '')}",
                'desc': desc
            })
    except:
        print(f"   ⚠️ Erro Trello: {cliente['nome_empresa']}")

# ==========================================
# INTELIGÊNCIA ARTIFICIAL CAMALEÃO (ROBUSTA)
# ==========================================
def buscar_lote_de_leads(cliente, nicho, quantidade):
    print(f"\n🕵️‍♂️ [IA] Prospectando para {cliente['nome_empresa']} no nicho: {nicho}...")
    
    prompt = f"""
    Encontre {quantidade} empresas corporativas do nicho de '{nicho}' ativas na cidade de '{cliente['cidade_base']}'.
    
    MISSÃO:
    Trabalhe para '{cliente['nome_empresa']}' vendendo '{cliente['produto_oferecido']}'.
    
    1. Ache Nome, Decisor, Site e adivinhe o e-mail (nome.sobrenome@dominio).
    2. 🚨 PESQUISE NO GOOGLE MEU NEGÓCIO / RECLAME AQUI: Encontre reclamações reais dos clientes deles.
    3. CRIE COPIES CONSULTIVAS (Diagnóstico Gratuito):
       - email_corpo: Focado na dor real encontrada e oferecendo diagnóstico.
       - linkedin_nota_conexao: Máximo 300 caracteres, foco em networking.
       - linkedin_inbox_1 e linkedin_inbox_2 (6 meses).
    
    Retorne estritamente um JSON array com chaves:
    nome_empresa, nome_socio, site_empresa, email_adivinhado, linkedin_decisor, linkedin_cto, nicho, 
    dor_identificada_para_o_produto, email_assunto, email_corpo, linkedin_nota_conexao, linkedin_inbox_1, linkedin_inbox_2.
    """
    try:
        resposta = client_ia.models.generate_content(
            model='gemini-2.5-flash', contents=prompt,
            config=types.GenerateContentConfig(tools=[{"google_search": {}}], temperature=0.7)
        )
        texto_limpo = resposta.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(texto_limpo)
    except Exception as e:
        print(f"   ❌ Erro Gemini: {e}")
        return []

def enviar_email_alerta_planilha(cliente, arquivo_excel):
    """Envia o alerta final com a planilha usando os dados do cliente."""
    remetente = cliente.get('email_remetente_disparo')
    senha = cliente.get('senha_email_disparo')
    destino = cliente.get('email_destino_alertas')
    
    if not remetente or not senha: return

    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = destino
    msg['Subject'] = f"🚀 Novos Leads ABM - {cliente['nome_empresa']}"
    
    corpo = "Segue em anexo a planilha de prospecção com dores reais detectadas e cadência agendada."
    msg.attach(MIMEText(corpo, 'plain'))

    try:
        with open(arquivo_excel, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(arquivo_excel)}")
            msg.attach(part)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(remetente, senha)
        server.sendmail(remetente, destino, msg.as_string())
        server.quit()
        print(f"   📧 Planilha enviada para {destino}")
    except:
        print("   ⚠️ Falha ao enviar e-mail de alerta.")

# Dentro da função buscar_lote_de_leads
def buscar_lote_de_leads(cliente, nicho, quantidade):
    # Se o nicho for uma lista de CNAEs específicos do IBGE
    cnaes = ", ".join(cliente.get('cnaes_especificos', []))
    
    prompt = f"""
    Busque empresas que se enquadrem nos seguintes CNAEs do IBGE: {cnaes}.
    Se a lista for 'TODOS', foque no setor de: {cliente.get('grupos_cnae')}.
    Localização: {cliente.get('cidades_alvo')}.
    ...
    """        

# ==========================================
# MOTOR PRINCIPAL MULTI-TENANT
# ==========================================
def rodar_caçada_geral(cliente_id_especifico=None):
    sb = get_supabase() # Ou como quer que você chame a conexão aí
    
    print("🕵️‍♂️ Iniciando motor de inteligência...")
    
    # SE RECEBER UM ID ESPECÍFICO, BUSCA SÓ ELE. SE NÃO, BUSCA TODOS.
    if cliente_id_especifico:
        res = sb.table("clientes").select("*").eq("id", cliente_id_especifico).execute()
    else:
        res = sb.table("clientes").select("*").eq("status_pagamento", "Em dia").execute()
        
    clientes = res.data
    
    if not clientes:
        print("❌ Nenhum cliente válido/ativo encontrado para prospecção.")
        return

    # Agora o seu laço "for" vai encontrar a variável perfeitamente!
    for cliente in clientes:
        print(f"🏢 Analisando alvo: {cliente.get('nome_empresa', 'Empresa Desconhecida')}")
        
        leads_mapeados = 0
        meta = cliente.get('meta_de_leads', 3)
        nichos = cliente.get('nichos_alvo', [])
        if not nichos: continue

        dados_para_planilha = []
        indice_nicho = 0
        
        while leads_mapeados < meta:
            nicho_atual = nichos[indice_nicho % len(nichos)]
            lote = buscar_lote_de_leads(cliente, nicho_atual, 2)
            
            for lead in lote:
                if leads_mapeados >= meta: break
                if verificar_lead_existente(lead['nome_empresa']): continue
                
                id_db = salvar_lead_supabase(lead, cliente['id'])
                if id_db:
                    agendar_cadencia_supabase(id_db, lead)
                    criar_card_trello(cliente, lead, id_db)
                    dados_para_planilha.append(lead)
                    leads_mapeados += 1
                    print(f"   ✅ Lead {leads_mapeados}/{meta} salvo!")
            
            indice_nicho += 1
            time.sleep(10)

        # Gera Excel e envia alerta por cliente
        if dados_para_planilha:
            df = pd.DataFrame(dados_para_planilha)
            nome_arq = f"Leads_{cliente['nome_empresa'].replace(' ', '_')}_{int(time.time())}.xlsx"
            df.to_excel(nome_arq, index=False)
            enviar_email_alerta_planilha(cliente, nome_arq)

    print("\n🏁 EXECUÇÃO GERAL CONCLUÍDA!")

if __name__ == "__main__":
    rodar_caçada_geral()