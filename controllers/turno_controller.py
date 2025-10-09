from database.session import get_db
from database.models import Turno

def consultar_turno(turno_id):
    """
    Consulta un turno por su ID.
    """
    db = next(get_db())
    turno = db.query(Turno).get(turno_id)
    if turno:
        return {
            "id": turno.id,
            "cliente": turno.cliente,
            "fecha": turno.fecha,
            "servicio": turno.servicio,
            "estado": turno.estado,
        }
    return None

def crear_turno(data):
    """
    Crea un nuevo turno.
    Args:
        data (dict): Diccionario con los datos del turno.
    Returns:
        dict: Turno creado.
    """
    db = next(get_db())
    turno = Turno(
        cliente=data['cliente'],
        fecha=data['fecha'],
        servicio=data['servicio'],
        estado=data.get('estado', 'pendiente')
    )
    db.add(turno)
    db.commit()
    db.refresh(turno)
    return {
        "id": turno.id,
        "cliente": turno.cliente,
        "fecha": turno.fecha,
        "servicio": turno.servicio,
        "estado": turno.estado,
    }

def actualizar_turno(turno_id, data):
    """
    Actualiza un turno existente.
    Args:
        turno_id (int): ID del turno.
        data (dict): Diccionario con campos a actualizar.
    Returns:
        dict: Turno actualizado o None si no existe.
    """
    db = next(get_db())
    turno = db.query(Turno).get(turno_id)
    if not turno:
        return None
    if 'cliente' in data:
        turno.cliente = data['cliente']
    if 'fecha' in data:
        turno.fecha = data['fecha']
    if 'servicio' in data:
        turno.servicio = data['servicio']
    if 'estado' in data:
        turno.estado = data['estado']
    db.commit()
    return {
        "id": turno.id,
        "cliente": turno.cliente,
        "fecha": turno.fecha,
        "servicio": turno.servicio,
        "estado": turno.estado,
    }

def eliminar_turno(turno_id):
    """
    Elimina un turno por su ID.
    Args:
        turno_id (int): ID del turno.
    Returns:
        bool: True si se eliminó, False si no existe.
    """
    db = next(get_db())
    turno = db.query(Turno).get(turno_id)
    if not turno:
        return False
    db.delete(turno)
    db.commit()
    return True

def listar_turnos():
    """
    Lista todos los turnos.
    Returns:
        list: Lista de turnos.
    """
    db = next(get_db())
    turnos = db.query(Turno).all()
    return [
        {
            "id": t.id,
            "cliente": t.cliente,
            "fecha": t.fecha,
            "servicio": t.servicio,
            "estado": t.estado,
        }
        for t in turnos
    ]