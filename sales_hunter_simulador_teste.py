import os
import sys
import json
import time
import urllib.parse
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

load_dotenv()

# --- CONEXÃO SUPABASE ---
def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

supabase = get_supabase()

# --- CREDENCIAIS IA ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client_ia = genai.Client(api_key=GEMINI_API_KEY)


def verificar_lead_existente(nome_empresa):
    try:
        resp = supabase.table("leads_hunter").select("id").ilike("nome_empresa", f"%{nome_empresa}%").execute()
        return len(resp.data) > 0
    except Exception as e:
        return False

def salvar_lead_supabase(lead, cliente_id):
    data = {
        "cliente_id": cliente_id,
        "nome_empresa": lead.get("nome_empresa", "Não informado"),
        "nicho_mercado": lead.get("nicho", ""),
        "nome_socio": lead.get("nome_socio", "Não encontrado"),
        "dor_presumida": lead.get("dor_identificada", "Não encontrada"),
        "status_funil": "🎯 Prospecção",
        "email": lead.get("email_adivinhado", ""),
        "links_redes_sociais": {
            "site": lead.get("site_empresa", ""),
            "linkedin_empresa": lead.get("linkedin_empresa", ""),
            "linkedin_decisor": lead.get("linkedin_decisor", "")
        }
    }
    try:
        response = supabase.table("leads_hunter").insert(data).execute()
        return response.data[0]['id'] 
    except Exception as e:
        print(f"   [DEBUG] Erro ao salvar no Supabase: {e}")
        return None

# ==========================================
# MÁGICA DA CADÊNCIA ACUMULATIVA (O FUNIL)
# ==========================================
def agendar_cadencia_supabase(lead_id, lead, cliente):
    if not lead_id: return
    
    canais_ativos = cliente.get('canais_prospeccao', [])
    hoje = datetime.now().date()
    soma_dias = 0
    tarefas = []

    linkedin_url = lead.get("linkedin_decisor", "")
    email_url = lead.get("email_adivinhado", "")
    telefone = lead.get("whatsapp_lead", "")
    empresa = lead.get("nome_empresa", "Empresa N/A")

    # 1. VISUALIZAR LINKEDIN
    if cliente.get('funil_visualizar_linkedin') and 'linkedin' in canais_ativos and linkedin_url:
        tarefas.append({"lead_id": lead_id, "empresa_lead": empresa, "tipo_acao": "visitar", "plataforma": "LinkedIn", "data_agendada": str(hoje), "contato_alvo": linkedin_url})

    # 2. CURTIR LINKEDIN
    if cliente.get('funil_curtir_linkedin') and 'linkedin' in canais_ativos and linkedin_url:
        soma_dias += int(cliente.get('funil_dias_curtir', 0))
        tarefas.append({"lead_id": lead_id, "empresa_lead": empresa, "tipo_acao": "curtir", "plataforma": "LinkedIn", "data_agendada": str(hoje + timedelta(days=soma_dias)), "contato_alvo": linkedin_url})

    # 3. ENVIAR E-MAIL
    if cliente.get('funil_enviar_email') and 'email' in canais_ativos and email_url:
        soma_dias += int(cliente.get('funil_dias_email', 0))
        tarefas.append({"lead_id": lead_id, "empresa_lead": empresa, "tipo_acao": "email", "plataforma": "Email", "data_agendada": str(hoje + timedelta(days=soma_dias)), "contato_alvo": email_url, "assunto_email": lead.get("email_assunto", ""), "copy_mensagem": lead.get("email_corpo", "")})

    # 4. CONECTAR LINKEDIN (Nota)
    if cliente.get('funil_conectar_linkedin') and 'linkedin' in canais_ativos and linkedin_url:
        soma_dias += int(cliente.get('funil_dias_conectar', 0))
        tarefas.append({"lead_id": lead_id, "empresa_lead": empresa, "tipo_acao": "conectar", "plataforma": "LinkedIn", "data_agendada": str(hoje + timedelta(days=soma_dias)), "contato_alvo": linkedin_url, "copy_mensagem": lead.get("linkedin_nota", "")})

    # 5. MENSAGEM WHATSAPP
    if cliente.get('funil_enviar_whatsapp') and 'whatsapp' in canais_ativos and telefone:
        soma_dias += int(cliente.get('funil_dias_whatsapp', 0))
        tarefas.append({"lead_id": lead_id, "empresa_lead": empresa, "tipo_acao": "whatsapp", "plataforma": "WhatsApp", "data_agendada": str(hoje + timedelta(days=soma_dias)), "contato_alvo": telefone, "copy_mensagem": lead.get("whatsapp_copy", "")})

    # 6. REMARKETING
    if cliente.get('funil_remarketing'):
        soma_dias += int(cliente.get('funil_dias_remarketing', 180))
        tarefas.append({"lead_id": lead_id, "empresa_lead": empresa, "tipo_acao": "remarketing", "plataforma": "CRM", "data_agendada": str(hoje + timedelta(days=soma_dias)), "contato_alvo": "N/A", "copy_mensagem": "Hora de reaquecer o lead."})

    try:
        if tarefas:
            supabase.table("cadencia_agendada").insert(tarefas).execute()
            print("   [DEBUG] Cadência dinâmica agendada perfeitamente no banco.")
    except Exception as e:
        print(f"   ⚠️ Erro ao agendar cadência: {e}")

# ==========================================
# BUSCA DE LEADS PELA IA
# ==========================================
def buscar_lote_de_leads(cliente, nicho_ou_cnae, quantidade):
    print(f"\n🧠 [IA] Gerando prompt para {quantidade} empresas...")
    
    locais = cliente.get('cidades_alvo', [])
    if "TODAS" in locais or not locais: locais = cliente.get('estados_alvo', ["Brasil"])
    localizacao = ", ".join(locais)

    prompt = f"""
    Encontre {quantidade} empresas corporativas reais no Google.
    SETOR/CNAE ALVO: '{nicho_ou_cnae}'
    LOCALIZAÇÃO: Focar em '{localizacao}'.
    
    Trabalhe para '{cliente.get('nome_empresa')}' vendendo '{cliente.get('produto_oferecido')}'.
    
    1. Ache Nome, Sócio, linkedin do decisor, e adivinhe o e-mail (ex: nome@dominio).
    2. Encontre um número de WhatsApp comercial (com DDD).
    3. Descubra uma dor provável.
    4. Gere copies curtas, diretas e persuasivas para:
       - email_assunto e email_corpo
       - linkedin_nota (máx 300 char)
       - whatsapp_copy (muito curta, tom natural de conversa, sem parecer robô).
    
    Retorne ESTRITAMENTE um array JSON contendo:
    nome_empresa, nome_socio, site_empresa, email_adivinhado, whatsapp_lead, linkedin_decisor, nicho, dor_identificada, email_assunto, email_corpo, linkedin_nota, whatsapp_copy.
    """
    try:
        resposta = client_ia.models.generate_content(
            model='gemini-2.5-flash', contents=prompt,
            config=types.GenerateContentConfig(tools=[{"google_search": {}}], temperature=0.7)
        )
        texto_limpo = resposta.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(texto_limpo)
    except Exception as e:
        print(f"❌ [IA] Erro crítico no Gemini: {e}")
        return []

# ==========================================
# MOTOR PRINCIPAL
# ==========================================
def rodar_cacada_geral(cliente_id):
    print("\n" + "="*50)
    print("🚀 INICIANDO AGENTE HUNTER")
    print("="*50)
    
    res = supabase.table("clientes").select("*").eq("id", cliente_id).execute()
    clientes = res.data
    if not clientes: return print("❌ Cliente não encontrado.")

    cliente = clientes[0]
    print(f"\n🏢 ALVO: {cliente.get('nome_empresa')}")
    
    meta = cliente.get('meta_de_leads', 3)
    alvos_busca = cliente.get('cnaes_especificos', []) if cliente.get('cnaes_especificos') else [cliente.get('produto_oferecido')]
    
    leads_mapeados = 0
    
    for nicho in alvos_busca:
        if leads_mapeados >= meta: break
        
        lote = buscar_lote_de_leads(cliente, nicho, 2)
        for lead in lote:
            if leads_mapeados >= meta: break
            
            if verificar_lead_existente(lead.get('nome_empresa')): continue
            
            id_db = salvar_lead_supabase(lead, cliente['id'])
            if id_db:
                agendar_cadencia_supabase(id_db, lead, cliente)
                leads_mapeados += 1
                print(f"   🟢 Lead {leads_mapeados}/{meta} registrado e Cadência criada!")

    print("\n🏁 CAÇADA CONCLUÍDA!")

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    if len(sys.argv) > 1:
        rodar_cacada_geral(sys.argv[1])
    else:
        print("⚠️ ERRO: ID do cliente não fornecido.")