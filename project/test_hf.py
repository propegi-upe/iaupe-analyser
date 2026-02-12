import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("HF_TOKEN")

headers = {
    "Authorization": f"Bearer {token}"
}

r = requests.get("https://huggingface.co/api/whoami-v2", headers=headers)

print("Status:", r.status_code)
print(r.text)
