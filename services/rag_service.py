import os
import chromadb
from chromadb.config import Settings
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
import dotenv
import os

dotenv.load_dotenv()

#Servicio de RAG (Retrieval-Augmented Generation) con ChromaDB y OpenAI Embeddings
class RagService:
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        embedding_model: str = "text-embedding-3-small",
        collections: List[str] = ["faqs", "productos", "politicas"],
        api_key: str = os.getenv("API_KEY")
    ):
        self.persist_directory = persist_directory

        # Inicializa Chroma con persistencia
        self.client = chromadb.PersistentClient(path=persist_directory)

        # Modelo de embeddings
        self.embedding_model = embedding_model
        self.embeddings = OpenAIEmbeddings(model=embedding_model, api_key=api_key)

        # Diccionario local para guardar colecciones
        self.collections = {}
        for col in collections:
            self._get_or_create_collection(col)

    def _get_or_create_collection(self, name: str):
        """Crea o recupera una colección existente."""
        if name not in self.collections:
            self.collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}  # usamos similitud coseno
            )
        return self.collections[name]

    # -----------------------------
    # 🔥 PUBLIC METHODS
    # -----------------------------

    def add_documents(
        self,
        collection_name: str,
        texts: List[str],
        metadatas: Optional[List[dict]] = None,
        chunk_size: int = 300,
        overlap_ratio: float = 0.10,
    ):
        """
        Chunking + Embedding + Store
        Almacena documentos con chunking + overlap + embeddings.
        """
        collection = self._get_or_create_collection(collection_name)

        chunks = []
        metadata_chunks = []

        for idx, text in enumerate(texts):
            text_chunks = self._chunk_text(text, chunk_size, overlap_ratio)
            for c_idx, chunk in enumerate(text_chunks):
                chunks.append(chunk)

                # Metadata por chunk
                metadata = metadatas[idx] if metadatas else {}
                metadata_chunks.append({
                    **metadata,
                    "chunk": c_idx,
                    "source_id": idx
                })

        # Crear IDs únicos
        ids = [f"{collection_name}_{i}" for i in range(len(chunks))]

        # Generar embeddings
        vectors = self.embeddings.embed_documents(chunks)

        # Guardar en Chroma
        collection.add(documents=chunks, embeddings=vectors, ids=ids, metadatas=metadata_chunks)

    def query_rag(self, collection_name: str, query: str, k: int = 3):
        """
        Busca los k documentos más relevantes según embeddings.
        Retorna una lista de textos + metadatas relevantes para contexto.
        """
        collection = self._get_or_create_collection(collection_name)

        query_embedding = self.embeddings.embed_query(query)

        results = collection.query(query_embeddings=[query_embedding], n_results=k)

        print("Resultados de la consulta RAG:", results) #DEBUG

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        return [
            {"text": doc, "metadata": meta}
            for doc, meta in zip(docs, metas)
        ]

    # -----------------------------
    # 🔧 INTERNAL UTILS
    # -----------------------------

    def _chunk_text(self, text: str, chunk_size: int, overlap_ratio: float):
        """Divide el texto en chunks con overlap."""
        overlap = int(chunk_size * overlap_ratio)
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap  # retrocede para el overlap

        return chunks

    def import_productos_from_csv(
        self,
        collection_name: str,
        csv_path: str,
        chunk_size: int = 300,
        overlap_ratio: float = 0.10
    ):
        """
        Importa un CSV de productos completo y lo guarda como documentos embebidos.
        El CSV debe contener: id, descripcion, cantidad, precio, categoria, color, talle, marca, genero, material
        """
        import pandas as pd

        df = pd.read_csv(csv_path)

        textos = []
        metadatas = []

        for _, row in df.iterrows():
            # Texto completo para embeddings con todas las columnas relevantes
            texto = (
                f"Producto: {row['descripcion']}.\n"
                f"Categoría: {row['categoria']}.\n"
                f"Color: {row['color']}.\n"
                f"Talle: {row['talle']}.\n"
                f"Marca: {row['marca']}.\n"
                f"Género: {row['genero']}.\n"
                f"Material: {row['material']}.\n"
                f"Precio: ${row['precio']}.\n"
                f"Stock: {row['cantidad']} unidades."
            )
            textos.append(texto)

            # Metadata enriquecida
            metadatas.append({
                "id": str(row["id"]),
                "descripcion": row["descripcion"],
                "categoria": row["categoria"],
                "color": row["color"],
                "talle": row["talle"],
                "marca": row["marca"],
                "genero": row["genero"],
                "material": row["material"],
                "precio": float(row["precio"]),
                "cantidad": int(row["cantidad"]),
                "source": os.path.basename(csv_path)
            })

        self.add_documents(
            collection_name=collection_name,
            texts=textos,
            metadatas=metadatas,
            chunk_size=chunk_size,
            overlap_ratio=overlap_ratio
        )

        print(f"✅ {len(df)} registros importados desde {csv_path} a la colección '{collection_name}'")
