# services/product_repository.py
from typing import List, Dict, Any, Optional
from services.rag_service import RagService
from utils.product_query_parser import parse_user_query
import math

class ProductRepository:
    """
    Repositorio para búsquedas híbridas en la colección 'productos'.
    Usa RagService (Chroma + embeddings) + product_query_parser (LLM).
    """

    def __init__(self, rag: Optional[RagService] = None, collection_name: str = "productos"):
        self.rag = rag or RagService()
        self.collection_name = collection_name

    def _build_where_clause(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Construye un where seguro para Chroma.
        Acepta múltiples filtros exactos.
        Ignora valores vacíos, None, dicts o listas.
        """
        where = {}
        allowed_keys = ("categoria", "color", "talle", "marca", "genero", "material")

        for key in allowed_keys:
            val = parsed.get(key)

            if not val:
                continue

            # Chroma SOLO acepta strings o valores primitivos simples
            # Si el parser te devuelve lista o dict → lo descartamos (o elegimos uno)
            if isinstance(val, (list, dict)):
                # Elegimos el primer valor válido si es lista
                if isinstance(val, list) and len(val) > 0:
                    val = str(val[0])
                else:
                    # Si es dict o algo raro → no lo usamos como filtro exacto
                    continue

            # Convertimos a string siempre
            where[key] = str(val).strip()

        return where


    def _post_filter(self, item_meta: Dict[str, Any], parsed: Dict[str, Any]) -> bool:
        """
        Filtrado adicional que Chroma no puede resolver solo.
        Soporta:
        - precio: rangos {gte, lte}
        - stock mínimo: stock o cantidad
        """

        # --- FILTRO DE PRECIO ---
        price_filter = parsed.get("precio")  # dict con gte/lte
        if price_filter:
            try:
                p = float(item_meta.get("precio", 0))
            except:
                return False  # si el precio no es numérico, se descarta

            gte = price_filter.get("gte")
            lte = price_filter.get("lte")

            if gte is not None and p < gte:
                return False
            if lte is not None and p > lte:
                return False

        # --- FILTRO DE STOCK ---
        stock_min = parsed.get("stock_min")
        if stock_min is not None:
            # Intentamos leer stock, si no existe: 0
            try:
                stock_val = int(item_meta.get("stock", item_meta.get("cantidad", 0)))
            except:
                stock_val = 0

            if stock_val < int(stock_min):
                return False

        return True


    def _distance_to_score(self, distance: float) -> float:
        """
        Convierte distancia (Chroma devuelve distancias; menor = mejor) a score 0..1 (mayor = mejor).
        Es heurístico: score = 1 / (1 + distance)
        """
        try:
            return 1.0 / (1.0 + float(distance))
        except:
            return 0.0

    def search_products(self, user_text: str) -> List[Dict[str, Any]]:
        """
        Flujo principal:
        1. Parsear query
        2. Construir where (exact filters)
        3. Generar embedding de consulta
        4. Query vectorial con where + n_results amplio
        5. Post-filtrar por precio/stock y re-rankear por distancia
        6. Devolver top-N (parsed['limit'])
        """
        parsed = parse_user_query(user_text)
        limit = parsed.get("limit", 8)

        # 1) Where: filtros exactos que aplicamos en Chroma
        where = self._build_where_clause(parsed)

        # 2) Query embedding (usamos el embed_query del RagService)
        query_text = parsed.get("consulta_texto") or user_text
        query_embedding = self.rag.embeddings.embed_query(query_text)

        # 3) Pedimos más resultados para tener margen de post-filtrado
        n_results = max(50, limit * 8)

        # Recuperamos la colección y ejecutamos query híbrida (vector + where)
        collection = self.rag._get_or_create_collection(self.collection_name)

        # Nota: algunos deployments de Chroma aceptan el parámetro `where` para filtrar metadata.
        # Si vuestra versión no lo soporta, pasad where={} y filtrad todo en post-proceso.
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
            )
        except TypeError:
            # Fallback si la signature no acepta where en esta versión:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )

        # results suele contener: documents, metadatas, distances, ids
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0] if "distances" in results else [math.inf] * len(docs)
        ids = results.get("ids", [[]])[0] if "ids" in results else [None] * len(docs)

        candidates = []
        for doc, meta, dist, _id in zip(docs, metas, distances, ids):
            # Post-filter por precio/stock (y cualquier otra lógica)
            if not self._post_filter(meta or {}, parsed):
                continue

            score = self._distance_to_score(dist)
            candidates.append({
                "id": (meta.get("id") if meta else _id),
                "text": doc,
                "metadata": meta,
                "distance": dist,
                "score": score
            })

        # Re-rank por score descendente
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # Retornar top-N
        return candidates[:limit]


# ===== Ejemplo de uso rápido =====
if __name__ == "__main__":
    repo = ProductRepository()
    queries = [
        "Tenés una remera roja talle M para mujer?",
        "Busco zapatillas nike entre 20000 y 40000, talle 42",
        "Remera oversize negra, marca adidas, precio hasta 15000"
    ]
    for q in queries:
        res = repo.search_products(q)
        print(f"\nConsulta: {q}")
        for r in res:
            print(f"- {r['id']} | score={r['score']:.4f} | {r['metadata']}")

