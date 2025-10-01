from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Crear motor
engine = create_engine(DATABASE_URL, echo=True)

# Sesiones
SessionLocal = sessionmaker(bind=engine)

# Crear tablas si no existen
Base.metadata.create_all(engine)
