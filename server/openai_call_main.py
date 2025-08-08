############### THIS FILE IS NOT IN USE ###############

from dotenv import load_dotenv
from database import Database
import os
import uuid
import cv2
import base64
import math
import uvicorn
import motor.motor_asyncio
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from datetime import datetime

app = FastAPI()
load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client.video_analysis_db
responses_collection = db.ai_responses

llm = ChatOpenAI(
    model="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
)

TEMP_DIR = "temp_videos"
os.makedirs(TEMP_DIR, exist_ok=True)


class VideoAnalysisRequest(BaseModel):
    video_id: str
    query: str


class VideoAnalysisResponse(BaseModel):
    video_id: str
    query: str
    response_id: str


class AIResponse(BaseModel):
    response_id: str
    response_text: str
    created_at: datetime


db_manager = None


@app.on_event("startup")
async def startup_event():
    global db_manager
    db_manager = Database()
    await db_manager.initialize()
    print("Database initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    global db_manager
    if db_manager:
        await db_manager.close()
        print("Database connection closed")


async def process_video(video_path: str, object_to_find: str):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Error opening video file")
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    max_frames = 10
    frame_interval = 1.0
    frame_indices = []
    current_time = 0.0
    while current_time < duration and len(frame_indices) < max_frames:
        frame_idx = math.floor(current_time * fps)
        frame_indices.append(frame_idx)
        current_time += frame_interval
    frames = []
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        success, frame = cap.read()
        if not success:
            continue
        frame = cv2.resize(frame, (640, 480))
        frames.append((idx, frame))
    cap.release()
    if not frames:
        raise ValueError("No frames were extracted from the video")
    encoded_frames = []
    for idx, frame in frames:
        _, buffer = cv2.imencode(".jpg", frame)
        encoded_image = base64.b64encode(buffer).decode("utf-8")
        encoded_frames.append((idx, encoded_image))
    prompt = f"""
    I'm providing {len(encoded_frames)} frames from a video in chronological order. 
    Please analyze these frames to track the movement and location of the {object_to_find}.
    
    For each frame:
    1. Identify if the {object_to_find} is present
    2. If present, describe its exact location (e.g., "top-left corner near the window", 
       "center of screen on the desk", "bottom-right being held by a person")
    3. Note any significant changes in position or appearance
    
    Finally, provide a summary of:
    - Where the {object_to_find} first appears
    - How it moves through the scene (direction, path)
    - Where it last appears
    - Any important interactions or changes
    
    Frame timestamps (in seconds): {[idx/fps for idx, _ in frames]}
    """
    # Create HumanMessage with all frames and prompt
    content = [{"type": "text", "text": prompt}]
    for _, encoded_image in encoded_frames:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"},
            }
        )
    message = HumanMessage(content=content)
    response = llm.invoke([message])
    return response.content


@app.get("/")
async def root():
    return {"message": "Hello from the Video Analysis Server!"}


@app.post("/api/analyze-video")
async def analyze_video(video: UploadFile = File(...), query: str = Form(...)):
    video_id = str(uuid.uuid4())
    video_path = os.path.join(TEMP_DIR, f"{video_id}.mp4")
    try:
        with open(video_path, "wb") as buffer:
            buffer.write(await video.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving video: {str(e)}")
    try:
        response_text = await process_video(video_path, query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")
    response_id = str(uuid.uuid4())
    # Store the response in MongoDB using db_manager
    response_data = {
        "response_id": response_id,
        "video_id": video_id,
        "query": query,
        "response_text": response_text,
        "created_at": datetime.now(),
    }
    try:
        await db_manager.store_response(response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing response: {str(e)}")
    return VideoAnalysisResponse(
        video_id=video_id, query=query, response_id=response_id
    )


@app.get("/api/ai-response", response_model=AIResponse)
async def ai_response(response_id: str):
    response = await db_manager.get_response(response_id)
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")
    return AIResponse(
        response_id=response["response_id"],
        response_text=response["response_text"],
        created_at=response["created_at"],
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
