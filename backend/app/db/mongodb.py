from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

db = MongoDB()

async def get_mongodb():
    if db.client is None:
        db.client = AsyncIOMotorClient(settings.MONGODB_URI)
        db.db = db.client[settings.DATABASE_NAME]
    return db.db

async def close_mongodb():
    if db.client:
        db.client.close()
        db.client = None
        db.db = None
