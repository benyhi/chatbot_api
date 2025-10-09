from database.session import get_db
from database.models import Producto

def consultar_producto(producto_id):
    """
    Consulta un producto por su ID.
    """
    db = next(get_db())
    producto = db.query(Producto).get(producto_id)
    if producto:
        return {
            "id": producto.id,
            "nombre": producto.name,
            "precio": producto.price,
        }
    return None

def crear_producto(data):
    """
    Crea un nuevo producto.
    Args:
        data (dict): Diccionario con 'name' y 'price'.
    Returns:
        dict: Producto creado.
    """
    db = next(get_db())
    producto = Producto(name=data['name'], price=data['price'])
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return {
        "id": producto.id,
        "nombre": producto.name,
        "precio": producto.price,
    }

def actualizar_producto(producto_id, data):
    """
    Actualiza un producto existente.
    Args:
        producto_id (int): ID del producto.
        data (dict): Diccionario con campos a actualizar.
    Returns:
        dict: Producto actualizado o None si no existe.
    """
    db = next(get_db())
    producto = db.query(Producto).get(producto_id)
    if not producto:
        return None
    if 'name' in data:
        producto.name = data['name']
    if 'price' in data:
        producto.price = data['price']
    db.commit()
    return {
        "id": producto.id,
        "nombre": producto.name,
        "precio": producto.price,
    }

def eliminar_producto(producto_id):
    """
    Elimina un producto por su ID.
    Args:
        producto_id (int): ID del producto.
    Returns:
        bool: True si se eliminó, False si no existe.
    """
    db = next(get_db())
    producto = db.query(Producto).get(producto_id)
    if not producto:
        return False
    db.delete(producto)
    db.commit()
    return True

def listar_productos():
    """
    Lista todos los productos.
    Returns:
        list: Lista de productos.
    """
    db = next(get_db())
    productos = db.query(Producto).all()
    return [
        {
            "id": p.id,
            "nombre": p.name,
            "precio": p.price,
        }
        for p in productos
    ]
