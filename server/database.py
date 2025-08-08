from dotenv import load_dotenv
import os
import motor.motor_asyncio
from pymongo import ASCENDING
from datetime import datetime

load_dotenv()


class Database:
    def __init__(self, uri: str = None, db_name: str = "video_analysis_db"):
        self.uri = uri or os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.client = motor.motor_asyncio.AsyncIOMotorClient(self.uri)
        self.db = self.client[db_name]
        self.responses_collection = self.db.ai_responses

    async def initialize(self):
        await self.responses_collection.create_index(
            [("response_id", ASCENDING)], unique=True
        )
        await self.responses_collection.create_index([("video_id", ASCENDING)])
        await self.responses_collection.create_index([("created_at", ASCENDING)])

    async def store_response(self, response_data: dict):
        response_data["created_at"] = datetime.now()
        result = await self.responses_collection.insert_one(response_data)
        return result.inserted_id

    async def get_response(self, response_id: str):
        return await self.responses_collection.find_one({"response_id": response_id})

    async def get_responses_by_video(self, video_id: str):
        cursor = self.responses_collection.find({"video_id": video_id}).sort(
            "created_at", ASCENDING
        )
        return await cursor.to_list(length=100)

    async def close(self):
        self.client.close()
