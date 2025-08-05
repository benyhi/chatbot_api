from .main import db, Product
from flask import jsonify, request

def consultar_producto(producto_id):
    """
    Consulta un producto por su ID.
    
    Args:
        producto_id (int): El ID del producto a consultar.
    
    Returns:
        dict: Información del producto si se encuentra, de lo contrario None.
    """
    producto = Product.query.get(producto_id)
    if producto:
        return {
            "id": producto.id,
            "nombre": producto.name,
            "precio": producto.price,
        }
    
    # Si no se encuentra el producto, retornar None
    return None

def crear_producto(data):
    """
    Crea un nuevo producto.
    Args:
        data (dict): Diccionario con 'name' y 'price'.
    Returns:
        dict: Producto creado.
    """
    producto = Product(name=data['name'], price=data['price'])
    db.session.add(producto)
    db.session.commit()
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
    producto = Product.query.get(producto_id)
    if not producto:
        return None
    if 'name' in data:
        producto.name = data['name']
    if 'price' in data:
        producto.price = data['price']
    db.session.commit()
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
    producto = Product.query.get(producto_id)
    if not producto:
        return False
    db.session.delete(producto)
    db.session.commit()
    return True

def listar_productos():
    """
    Lista todos los productos.
    Returns:
        list: Lista de productos.
    """
    productos = Product.query.all()
    return [
        {
            "id": p.id,
            "nombre": p.name,
            "precio": p.price,
        }
        for p in productos
    ]
