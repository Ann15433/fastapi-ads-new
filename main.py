from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Настройка базы данных (SQLite для простоты)
SQLALCHEMY_DATABASE_URL = "sqlite:///./ads.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # Исправлено: autoflush
Base = declarative_base()

# Модель базы данных
class AdvertisementDB(Base):
    __tablename__ = "advertisements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    price = Column(Float)
    author = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic модели (адаптированы под Pydantic 2)
class AdvertisementBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # Замена Config
    title: str
    description: str
    price: float
    author: str

class AdvertisementCreate(AdvertisementBase):
    pass

class AdvertisementUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    author: Optional[str] = None

class AdvertisementResponse(AdvertisementBase):
    id: int
    created_at: datetime

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Advertisement Service")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/advertisement", response_model=AdvertisementResponse)
def create_advertisement(advertisement: AdvertisementCreate):
    db = next(get_db())
    db_advertisement = AdvertisementDB(**advertisement.model_dump())  # Исправлено: model_dump()
    db.add(db_advertisement)
    db.commit()
    db.refresh(db_advertisement)
    return db_advertisement

@app.get("/advertisement/{advertisement_id}", response_model=AdvertisementResponse)
def read_advertisement(advertisement_id: int):
    db = next(get_db())
    advertisement = db.query(AdvertisementDB).filter(AdvertisementDB.id == advertisement_id).first()
    if advertisement is None:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    return advertisement

@app.patch("/advertisement/{advertisement_id}", response_model=AdvertisementResponse)
def update_advertisement(advertisement_id: int, advertisement: AdvertisementUpdate):
    db = next(get_db())
    db_advertisement = db.query(AdvertisementDB).filter(AdvertisementDB.id == advertisement_id).first()
    if db_advertisement is None:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    update_data = advertisement.model_dump(exclude_unset=True)  # Исправлено: model_dump()
    for key, value in update_data.items():
        setattr(db_advertisement, key, value)
    db.commit()
    db.refresh(db_advertisement)
    return db_advertisement

@app.delete("/advertisement/{advertisement_id}")
def delete_advertisement(advertisement_id: int):
    db = next(get_db())
    advertisement = db.query(AdvertisementDB).filter(AdvertisementDB.id == advertisement_id).first()
    if advertisement is None:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    db.delete(advertisement)
    db.commit()
    return {"message": "Advertisement deleted successfully"}

@app.get("/advertisement", response_model=List[AdvertisementResponse])
def search_advertisements(
        title: Optional[str] = Query(None, description="Поиск по заголовку"),
        author: Optional[str] = Query(None, description="Поиск по автору"),
        min_price: Optional[float] = Query(None, description="Минимальная цена"),
        max_price: Optional[float] = Query(None, description="Максимальная цена")
):
    db = next(get_db())
    query = db.query(AdvertisementDB)

    if title:
        query = query.filter(AdvertisementDB.title.contains(title))
    if author:
        query = query.filter(AdvertisementDB.author.contains(author))
    if min_price is not None:
        query = query.filter(AdvertisementDB.price >= min_price)
    if max_price is not None:
        query = query.filter(AdvertisementDB.price <= max_price)

    return query.all()
