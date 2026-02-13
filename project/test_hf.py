import os
import requests
from dotenv import load_dotenv

# Carrega variáveis do arquivo project/.env (ex.: HF_TOKEN)
load_dotenv()

# Busca token do ambiente
token = os.getenv("HF_TOKEN")

# Monta header de autenticação no padrão Bearer
headers = {
    "Authorization": f"Bearer {token}"
}

# Endpoint simples para validar se o token é aceito e identificar o usuário
r = requests.get("https://huggingface.co/api/whoami-v2", headers=headers)

# Imprime status e resposta (útil para depurar token ausente/inválido)
print("Status:", r.status_code)
print(r.text)
