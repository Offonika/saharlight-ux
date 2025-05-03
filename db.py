# db.py
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Float, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    telegram_id = Column(BigInteger, primary_key=True, index=True)
    thread_id = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Profile(Base):
    __tablename__ = 'profiles'
    telegram_id = Column(BigInteger, ForeignKey('users.telegram_id'), primary_key=True)
    icr = Column(Float)
    cf = Column(Float)
    target_bg = Column(Float)
    user = relationship('User')

class Entry(Base):
    __tablename__ = 'entries'
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, ForeignKey('users.telegram_id'))
    timestamp = Column(TIMESTAMP, server_default=func.now())
    photo_path = Column(String)
    carbs_g = Column(Float)
    xe = Column(Float)
    sugar_before = Column(Float)
    dose = Column(Float)
    gpt_summary = Column(Text)

def init_db():
    Base.metadata.create_all(bind=engine)
