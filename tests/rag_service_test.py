from services.rag_service import RagService

rag = RagService()

rag.import_productos_from_csv(collection_name="productos",csv_path="database/csv/tienda_ropa_500.csv")

res = rag.query_rag(collection_name="productos", query="¿Tienen camisetas rojas en talla M?")

print(res)
