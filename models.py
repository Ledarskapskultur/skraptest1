from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

Base = declarative_base()

class Kurs(Base):
    __tablename__ = 'kurser'

    id = Column(Integer, primary_key=True)
    namn = Column(String)
    datum = Column(String)
    platser = Column(String)
    plats = Column(String)
    pris = Column(String)
    hemsida = Column(String)
    maps = Column(String)
    handledare = Column(String)
