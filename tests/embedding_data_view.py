import pandas as pd
from openai import OpenAI
import chromadb
from chromadb.config import Settings
import umap
import plotly.express as px
import uuid
import dotenv
import os

dotenv.load_dotenv()

# === CONFIG ===
CSV_PATH = "D:\\proyectos\\chatbot_api\\database\\csv\\tienda_ropa_1000.csv"   # Ruta a tu CSV
OPENAI_API_KEY = os.getenv("API_KEY")
EMBED_MODEL = "text-embedding-3-small"  # O usa text-embedding-3-large para +precisión

client = OpenAI(api_key=OPENAI_API_KEY)

# === 1. Cargar CSV ===
df = pd.read_csv(CSV_PATH)

# Creamos el texto para embebido, podés ajustar si querés agregar info
df["text"] = df.apply(lambda row: 
                      f"{row['descripcion']} - Categoria: {row['categoria']} - Talle: {row['talle']}",
                      axis=1)

# === 2. Generar Embeddings ===
def embed_batch(texts):
    return client.embeddings.create(
        model=EMBED_MODEL,
        input=texts
    ).data

embeddings = []
batch_size = 50

for i in range(0, len(df), batch_size):
    batch = df["text"][i:i+batch_size].tolist()
    response = embed_batch(batch)
    for emb in response:
        embeddings.append(emb.embedding)

df["embedding"] = embeddings

# === 3. Guardar en una base vectorial (ChromaDB local) ===
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(
    name="ropa",
    metadata={"hnsw:space": "cosine"}
)

for idx, row in df.iterrows():
    collection.add(
        ids=[str(uuid.uuid4())],
        embeddings=[row["embedding"]],
        metadatas=[{
            "descripcion": row["descripcion"],
            "categoria": row["categoria"],
            "talle": row["talle"],
            "precio": row["precio"],
            "cantidad": row["cantidad"]
        }],
        documents=[row["text"]]
    )

print("✅ Datos cargados en ChromaDB")

# === 4. Reducir a 3D con UMAP para visualizar ===
reducer = umap.UMAP(
    n_components=3,
    n_neighbors=30,
    min_dist=0.1,
    metric="cosine",
    random_state=42
)

embedding_3d = reducer.fit_transform(list(df["embedding"]))

df["x"] = embedding_3d[:, 0]
df["y"] = embedding_3d[:, 1]
df["z"] = embedding_3d[:, 2]

# === 5. Visualización 3D ===
fig = px.scatter_3d(
    df,
    x="x",
    y="y",
    z="z",
    color="categoria",
    hover_data=["descripcion", "talle", "precio"],
    title="Mapa Vectorial 3D de Productos (UMAP)"
)

import webbrowser
import plotly.offline as pyo

output_file = "embedding_map_3d.html"
pyo.plot(fig, filename=output_file, auto_open=False)
print(f"Mapa 3D generado en {output_file}")
webbrowser.open(output_file)