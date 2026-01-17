from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)

    exchanges = relationship("ExchangeAccount", back_populates="owner")

class ExchangeAccount(Base):
    __tablename__ = "exchange_accounts"
    id = Column(Integer, primary_key=True)
    exchange_name = Column(String) 
    
    api_key = Column(String)
    api_secret = Column(String)
    api_passphrase = Column(String, nullable=True)
    is_demo = Column(Boolean, default=False)
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="exchanges")