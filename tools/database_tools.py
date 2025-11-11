from langchain.tools import tool
from controllers.producto_controller import consultar_producto, crear_producto, actualizar_producto, eliminar_producto

@tool
def get_product(producto: str):
    """Obtiene información de un producto por su identificador (por ejemplo, código o ID)."""
    return consultar_producto(producto)

@tool
def create_product(data: dict):
    """Crea un nuevo producto en la base de datos con los datos proporcionados."""
    return crear_producto(data)