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
            You are analyzing a video for the presence of a specific object. The query is: "{object_to_find}".

            Your ONLY task:
            1. Determine if the object in the query is visible in any frame provided.
            2. If visible, answer "Yes" and:
            - Describe its **exact location** in the scene with clear reference points.
            - Give **timestamps** (approximate to the nearest second) when it first appears, changes position, or disappears.
            - Mention any **relevant surrounding objects** or context that help identify it.
            - Provide a short, factual description in **2 to 3 sentences max**.
            3. If NOT visible, answer "No" and say: "The object was not found in the video."
            4. Do NOT talk about unrelated objects, people, or background unless they help locate the object.

            Be factual, concise, and specific.

            Example 1:
            Query: "Can you see my laptop?"
            AI Response: "Yes. Seen at 00:06 on the bed with a patterned mattress, open and connected by a black cable. Last visible at 00:10 near the dark brown headboard with a phone placed beside it."

            Example 2:
            Query: "Is there a red car?"
            AI Response: "Yes. First appears at 00:03 on the left side of the street beside a white van. Moves to the center of the frame by 00:07 before leaving the scene at 00:09."

            Example 3:
            Query: "Can you see my black backpack?"
            AI Response: "No. The object was not found in the video."

            Example 4:
            Query: "Do you see a white dog?"
            AI Response: "Yes. Appears at 00:02 near the wooden fence on the right side of the garden. Stays in view until 00:05, playing with a red ball near a metal chair."
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
