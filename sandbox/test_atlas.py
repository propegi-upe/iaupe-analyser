from dotenv import load_dotenv

load_dotenv(override=True)

from pymongo import MongoClient
import os

uri = os.getenv("MONGODB_URI")
client = MongoClient(uri)
db = client[os.getenv("MONGODB_DB", "iaupe-analyser")]
print("Conectado no DB:", db.name)
print("Collections:", db.list_collection_names())