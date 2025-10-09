from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False) 
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now())

class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    descripcion = Column(Text)
    precio = Column(Integer, nullable=False)
    stock = Column(Integer, default=0)

class Turno(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente = Column(String, nullable=False)
    fecha = Column(DateTime, nullable=False)
    servicio = Column(String, nullable=False)
    estado = Column(String, default="pendiente") 