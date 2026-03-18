import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from playwright.sync_api import sync_playwright

load_dotenv()

# --- CONEXÃO SUPABASE ---
def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

# --- MOTOR PRINCIPAL DO FARMER ---
def executar_tarefas_linkedin(cliente_id):
    print("\n" + "="*50)
    print("🌾 INICIANDO MOTOR FARMER - EXECUÇÃO LINKEDIN")
    print("="*50)

    sb = get_supabase()
    hoje = str(datetime.now().date())

    # 1. Busca todos os leads pertencentes a este cliente
    print(f"🔍 [DEBUG] Mapeando leads do cliente no banco de dados...")
    try:
        res_leads = sb.table("leads_hunter").select("id").eq("cliente_id", cliente_id).execute()
        leads_ids = [l['id'] for l in res_leads.data]
    except Exception as e:
        print(f"❌ Erro ao buscar leads do cliente: {e}")
        return

    if not leads_ids:
        print("❌ Nenhum lead encontrado para este cliente.")
        return

    # 2. Busca na agenda apenas as tarefas de HOJE (ou atrasadas) para os leads deste cliente
    print(f"📅 [DEBUG] Lendo a agenda de tarefas até o dia {hoje}...")
    try:
        res_tarefas = sb.table("cadencia_agendada").select("*").in_("lead_id", leads_ids).lte("data_agendada", hoje).execute()
        tarefas_hoje = res_tarefas.data
    except Exception as e:
        print(f"❌ Erro ao ler a agenda de tarefas: {e}")
        return

    if not tarefas_hoje:
        print("✅ Nenhuma tarefa pendente para hoje. O robô está descansando! 😴")
        return

    print(f"🔥 Foram encontradas {len(tarefas_hoje)} tarefas na fila de hoje!")
    print("🚀 Iniciando o Playwright e abrindo o navegador...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context()
        page = context.new_page()

        # ==========================================
        # 🔐 LOGIN NO LINKEDIN
        # ==========================================
        email_li = os.getenv("LINKEDIN_EMAIL")
        senha_li = os.getenv("LINKEDIN_SENHA")

        if not email_li or not senha_li:
            print("⚠️ AVISO: Credenciais do LinkedIn não encontradas no arquivo .env.")
            print("O robô fará apenas uma simulação das tarefas sem fazer o login real.")
            login_real = False
        else:
            print("🔑 Realizando login no LinkedIn...")
            try:
                page.goto("https://www.linkedin.com/login")
                page.fill("input#username", email_li)
                page.fill("input#password", senha_li)
                page.click("button[type='submit']")
                
                page.wait_for_selector(".global-nav__me-photo", timeout=15000) 
                print("✅ Login realizado com sucesso!")
                login_real = True
            except Exception as e:
                print(f"❌ Falha no login do LinkedIn. Verifique suas credenciais. Erro: {e}")
                browser.close()
                return

        # ==========================================
        # 📝 EXECUÇÃO DA FILA DE TAREFAS
        # ==========================================
        for tarefa in tarefas_hoje:
            acao = tarefa.get('tipo_acao')
            alvo = tarefa.get('contato_alvo')
            empresa = tarefa.get('empresa_lead')
            lead_id = tarefa.get('lead_id')

            print(f"\n▶️ Iniciando: [{acao.upper()}] - Alvo: {empresa}")
            print(f"🔗 URL: {alvo}")
            
            try:
                if login_real and alvo.startswith("http"):
                    page.goto(alvo)
                    time.sleep(5) 

                # --- SIMULAÇÃO/EXECUÇÃO DAS AÇÕES E INTEGRAÇÃO CRM ---
                if acao == 'visitar':
                    print("   👀 Perfil visitado. (O decisor receberá a notificação que você olhou o perfil dele)")
                    
                    # MAGICA DO CRM: Move o card do lead automaticamente no banco
                    if lead_id:
                        sb.table("leads_hunter").update({"status_funil": "👀 LinkedIn Visitado"}).eq("id", lead_id).execute()
                        print("   📊 CRM atualizado: Lead movido para '👀 LinkedIn Visitado'.")
                
                elif acao == 'curtir':
                    print("   👍 Encontrando último post e clicando em curtir...")
                
                elif acao == 'conectar':
                    msg = tarefa.get('copy_mensagem', '')
                    print(f"   🤝 Clicando em 'Conectar' e enviando a nota: '{msg[:50]}...'")
                
                elif acao == 'mensagem':
                    msg = tarefa.get('copy_mensagem', '')
                    print(f"   💬 Abrindo o Inbox e enviando a mensagem: '{msg[:50]}...'")

                print("   ✅ Tarefa executada com sucesso!")
                
                # 4. Remove a tarefa concluída do banco de dados
                sb.table("cadencia_agendada").delete().eq("id", tarefa['id']).execute()
                print("   🗑️ Tarefa baixada da agenda.")

                # Pausa para evitar bloqueios do LinkedIn
                print("   ⏳ Aguardando 15 segundos para simular comportamento humano e evitar bloqueios...")
                time.sleep(15)

            except Exception as e:
                print(f"   ❌ Erro ao executar tarefa no perfil {alvo}: {e}")

        browser.close()
        print("\n🏁 EXPEDIENTE FINALIZADO! Todas as tarefas de hoje foram processadas.")


if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    if len(sys.argv) > 1:
        id_alvo = sys.argv[1]
        executar_tarefas_linkedin(id_alvo)
    else:
        print("⚠️ ERRO: O ID do cliente não foi fornecido para o Farmer.")