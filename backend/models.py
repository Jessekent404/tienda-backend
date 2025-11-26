from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str
    price: float
    image: str
    description: str
    specs: List[str] = []
    rating: float = 4.5
    reviews: int = 0
    featured: bool = False
    affiliateLink: str
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

class ProductCreate(BaseModel):
    name: str
    category: str
    price: float
    image: str
    description: str
    specs: List[str] = []
    rating: float = 4.5
    reviews: int = 0
    featured: bool = False
    affiliateLink: str

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    image: Optional[str] = None
    description: Optional[str] = None
    specs: Optional[List[str]] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    featured: Optional[bool] = None
    affiliateLink: Optional[str] = None

class Category(BaseModel):
    id: int
    name: str
    slug: str
    image: str
    description: str

class AdminLogin(BaseModel):
    username: str
    password: str

class AdminToken(BaseModel):
    token: str
    username: str
