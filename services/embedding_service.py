import pandas as pd
import chromadb
from openai import OpenAI
from chromadb.config import Settings
from uuid import uuid4
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("API_KEY"))

# ---- Cargar datos de productos ----
df = pd.read_csv("database/csv/tienda_ropa_1000.csv")

# ---- Crear instancia de Chroma ----
chroma_client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet",
                                         persist_directory="chroma_db"))
collection = chroma_client.get_or_create_collection(
    name="productos",
    metadata={"hnsw:space": "cosine"}  # métrica de similitud
)

# ---- Convertir cada producto en un chunk de texto ----
documents = []
metadatas = []
ids = []

for _, row in df.iterrows():
    texto = f"{row['descripcion']} - Categoria: {row['categoria']} - Talle: {row['talle']} - Precio: {row['precio']} - Stock: {row['cantidad']} unidades"
    
    documents.append(texto)
    metadatas.append({"categoria": row['categoria'], "talle": row['talle']})
    ids.append(str(uuid4()))  # id único por registro

# ---- Crear embeddings y guardar en Chroma ----
collection.add(
    documents=documents,
    metadatas=metadatas,
    ids=ids
)

print("✅ Embeddings creados y guardados en Chroma con éxito.")
