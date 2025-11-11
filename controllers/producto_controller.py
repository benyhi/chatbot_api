from database.session import get_db
from sqlalchemy import or_
from database.models import Producto

def consultar_producto(producto: str | int = None) -> dict | None:
    """
    Consulta un producto por su nombre o código.
    """
    db = next(get_db())

    if producto is not None and isinstance(producto, str):
        producto = db.query(Producto).filter(or_(Producto.nombre.like(f"%{producto}%"), Producto.codigo.like(f"%{producto}%"))).first()

    if producto:
        return {
            "id": producto.id,
            "codigo": producto.codigo,
            "nombre": producto.nombre,
            "descripcion": producto.descripcion,
            "precio": producto.precio,
            "stock": producto.stock,
        }
    
    return None

def crear_producto(data):
    """
    Crea un nuevo producto.
    Args:
        data (dict): Diccionario con 'codigo', 'nombre', 'descripcion', 'precio', 'stock'.
    Returns:
        dict: Producto creado.
    """
    
    db = next(get_db())

    producto = Producto(
        codigo=data['codigo'],
        nombre=data['nombre'],
        descripcion=data.get('descripcion', ''),
        precio=data['precio'],
        stock=data.get('stock', 0)
    )
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return {
        "id": producto.id,
        "codigo": producto.codigo,
        "nombre": producto.nombre,
        "descripcion": producto.descripcion,
        "precio": producto.precio,
        "stock": producto.stock,
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
    if 'codigo' in data:
        producto.codigo = data['codigo']
    if 'nombre' in data:
        producto.nombre = data['nombre']
    if 'descripcion' in data:
        producto.descripcion = data['descripcion']
    if 'precio' in data:
        producto.precio = data['precio']
    if 'stock' in data:
        producto.stock = data['stock']
    db.commit()
    return {
        "id": producto.id,
        "codigo": producto.codigo,
        "nombre": producto.nombre,
        "descripcion": producto.descripcion,
        "precio": producto.precio,
        "stock": producto.stock,
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
            "codigo": p.codigo,
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "precio": p.precio,
            "stock": p.stock,
        }
        for p in productos
    ]
