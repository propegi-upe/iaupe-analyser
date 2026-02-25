import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Busca token do ambiente
token = os.getenv("HF_TOKEN")

headers = {
    "Authorization": f"Bearer {token}"
}

# endpoint  para validar se o token é aceito e identificar o usuário 
r = requests.get("https://huggingface.co/api/whoami-v2", headers=headers)

print("Status:", r.status_code)
print(r.text)