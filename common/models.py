from sqlalchemy import Column, String, Float, DateTime, Integer
from .database import Base
import datetime

class User(Base):
    __tablename__ = 'users'
    email = Column(String, primary_key=True, index=True)
    ticker = Column(String)

class FinancialData(Base):
    __tablename__ = 'financial_data'
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    value = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
