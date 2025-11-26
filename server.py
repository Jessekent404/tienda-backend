from fastapi import FastAPI, APIRouter, HTTPException, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List
import uuid
from datetime import datetime, timezone, timedelta
from models import Product, ProductCreate, ProductUpdate, Category, AdminLogin, AdminToken
from auth import verify_admin_credentials, create_access_token, verify_token


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# ===================== ADMIN AUTH ROUTES =====================
@api_router.post("/admin/login", response_model=AdminToken)
async def admin_login(credentials: AdminLogin):
    """Login de administrador"""
    if not verify_admin_credentials(credentials.username, credentials.password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    access_token = create_access_token(
        data={"sub": credentials.username},
        expires_delta=timedelta(hours=24)
    )
    return AdminToken(token=access_token, username=credentials.username)

@api_router.get("/admin/verify")
async def verify_admin(username: str = Depends(verify_token)):
    """Verificar si el token es válido"""
    return {"valid": True, "username": username}

# ===================== PRODUCTS ROUTES =====================
@api_router.get("/products", response_model=List[Product])
async def get_products():
    """Obtener todos los productos"""
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    return products

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    """Obtener un producto por ID"""
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product

@api_router.post("/products", response_model=Product)
async def create_product(product: ProductCreate, username: str = Depends(verify_token)):
    """Crear un nuevo producto (requiere autenticación)"""
    product_dict = product.model_dump()
    new_product = Product(**product_dict)
    
    doc = new_product.model_dump()
    doc['createdAt'] = doc['createdAt'].isoformat()
    doc['updatedAt'] = doc['updatedAt'].isoformat()
    
    await db.products.insert_one(doc)
    return new_product

@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(
    product_id: str, 
    product_update: ProductUpdate,
    username: str = Depends(verify_token)
):
    """Actualizar un producto (requiere autenticación)"""
    existing_product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not existing_product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    update_data = product_update.model_dump(exclude_unset=True)
    update_data['updatedAt'] = datetime.utcnow().isoformat()
    
    await db.products.update_one(
        {"id": product_id},
        {"$set": update_data}
    )
    
    updated_product = await db.products.find_one({"id": product_id}, {"_id": 0})
    return Product(**updated_product)

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, username: str = Depends(verify_token)):
    """Eliminar un producto (requiere autenticación)"""
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"message": "Producto eliminado exitosamente"}

# ===================== CATEGORIES ROUTES =====================
@api_router.get("/categories", response_model=List[Category])
async def get_categories():
    """Obtener todas las categorías"""
    categories = [
        Category(
            id=1,
            name="Electrónica",
            slug="electronica",
            image="https://images.unsplash.com/photo-1717996563514-e3519f9ef9f7",
            description="Tecnología moderna y gadgets innovadores"
        ),
        Category(
            id=2,
            name="Hogar y Cocina",
            slug="hogar-cocina",
            image="https://images.unsplash.com/photo-1616046229478-9901c5536a45",
            description="Productos elegantes para tu hogar"
        ),
        Category(
            id=3,
            name="Moda y Accesorios",
            slug="moda-accesorios",
            image="https://images.unsplash.com/photo-1569388330292-79cc1ec67270",
            description="Estilo y sofisticación en cada pieza"
        ),
        Category(
            id=4,
            name="Salud y Belleza",
            slug="salud-belleza",
            image="https://images.unsplash.com/photo-1598528738936-c50861cc75a9",
            description="Bienestar y cuidado personal premium"
        ),
        Category(
            id=5,
            name="Deportes y Fitness",
            slug="deportes-fitness",
            image="https://images.unsplash.com/photo-1627257058769-0a99529e4312",
            description="Equipamiento para tu vida activa"
        )
    ]
    return categories

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()