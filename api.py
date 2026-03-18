from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import sys
import os

app = FastAPI(title="DJM SaaS API")

# Isso é vital: Permite que o React (que roda na porta 5173) converse com o Python (porta 8000) sem bloqueios de segurança
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def executar_robo(nome_script: str, cliente_id: str):
    print(f"🤖 Iniciando {nome_script} para o cliente {cliente_id}...")
    try:
        env_vars = os.environ.copy()
        env_vars["PYTHONIOENCODING"] = "utf-8"
        
        # Roda o script de forma invisível no servidor
        subprocess.run(
            [sys.executable, "-u", nome_script, str(cliente_id)],
            env=env_vars,
            check=True
        )
        print(f"✅ {nome_script} finalizado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao rodar {nome_script}: {e}")

# Rota que o botão "Hunter" vai chamar
@app.post("/api/hunter/{cliente_id}")
async def iniciar_hunter(cliente_id: str, background_tasks: BackgroundTasks):
    # Usa BackgroundTasks para o React não ficar com a tela travada esperando o robô acabar
    background_tasks.add_task(executar_robo, "sales_hunter_simulador_teste.py", cliente_id)
    return {"status": "sucesso", "mensagem": "Caçada iniciada nos bastidores!"}

# Rota que o botão "Farmer" vai chamar
@app.post("/api/farmer/{cliente_id}")
async def iniciar_farmer(cliente_id: str, background_tasks: BackgroundTasks):
    # Alterado para o novo nome do script unificado
    background_tasks.add_task(executar_robo, "sales_farmer.py", cliente_id)
    return {"status": "sucesso", "mensagem": "Agente Farmer Multi-Canal Acionado!"}

if __name__ == "__main__":
    import uvicorn
    # Roda a API na porta 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)