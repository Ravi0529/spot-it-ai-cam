# SpotIt AI Cam

A powerful AI-powered video analysis system that can detect and locate specific objects within video content using OpenAI's GPT-4 Vision and LangChain.

## 🚀 Features

- **AI-Powered Video Analysis**: Uses OpenAI's GPT-4 Vision model to analyze video content
- **Object Detection & Localization**: Find specific objects and provide detailed location information
- **Timestamp Tracking**: Get precise timestamps when objects appear, move, or disappear
- **Context-Aware Analysis**: Understand surrounding objects and scene context
- **RESTful API**: Clean FastAPI endpoints for easy integration
- **MongoDB Storage**: Persistent storage of analysis results
- **Docker Support**: Easy deployment with Docker and Docker Compose

## 🏗️ Architecture

### Backend Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **OpenAI GPT-4 Vision**: Advanced AI model for video frame analysis
- **LangChain**: Framework for building AI applications
- **MongoDB**: NoSQL database for storing analysis responses
- **OpenCV**: Computer vision library for video processing
- **Motor**: Async MongoDB driver for Python

### Key Components

- **Video Processing**: Extracts key frames from uploaded videos
- **AI Analysis**: Sends frames to GPT-4 Vision for object detection
- **Response Management**: Stores and retrieves analysis results
- **Database Layer**: Async MongoDB operations with proper indexing

## 📋 Prerequisites

- Python 3.11+
- Docker and Docker Compose
- OpenAI API key
- MongoDB (included in Docker setup)

## 🛠️ Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/Ravi0529/spot-it-ai-cam.git
   cd spot-it-ai-cam
   ```

2. **Set up environment variables**
   Create a `.env` file in the root directory:

   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   MONGO_URI=mongodb://mongo:27017
   ```

3. **Run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

## 🚀 Usage

### API Endpoints

#### 1. Analyze Video

```http
POST /api/analyze-video
Content-Type: multipart/form-data

video: [video_file]
query: "Can you see my laptop?"
```

**Response:**

```json
{
  "video_id": "uuid",
  "query": "Can you see my laptop?",
  "response_id": "response_uuid"
}
```

#### 2. Get Analysis Results

```http
GET /api/ai-response?response_id={response_id}
```

**Response:**

```json
{
  "response_id": "uuid",
  "response_text": "Yes. Seen at 00:06 on the bed with a patterned mattress...",
  "created_at": "2024-01-01T12:00:00"
}
```

### Example Queries

- "Can you see my laptop?"
- "Is there a red car?"
- "Do you see a white dog?"
- "Can you find my black backpack?"

## 🔧 Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key
- `MONGO_URI`: MongoDB connection string
- `TEMP_DIR`: Directory for temporary video storage

### Docker Configuration

- **API Service**: Runs on port 8000
- **MongoDB**: Runs on port 27017
- **Volume Mounts**: Persistent storage for videos and database

## 📁 Project Structure

```
SpotIt-AI-cam/
├── server/
│   ├── main.py              # FastAPI application
│   ├── database.py          # MongoDB operations
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile          # Container configuration
├── docker-compose.yaml      # Multi-container setup
├── .env                     # Environment variables
└── README.md               # This file
```

## 🐳 Docker Details

### API Container

- **Base Image**: Python 3.11-slim-bookworm
- **Dependencies**: OpenCV, FFmpeg, OpenGL libraries
- **Port**: 8000
- **Volume**: Mounts server code and temp_videos directory

### MongoDB Container

- **Base Image**: MongoDB latest
- **Port**: 27017
- **Volume**: Persistent data storage

## 🔍 How It Works

1. **Video Upload**: Client uploads video file with analysis query
2. **Frame Extraction**: System extracts 10 key frames at 1-second intervals
3. **AI Analysis**: Frames are sent to GPT-4 Vision with specific prompt
4. **Response Generation**: AI provides detailed object location and timing
5. **Storage**: Results are stored in MongoDB for future retrieval
6. **Response**: Analysis results returned to client

## 🚧 Development

### Local Development

```bash
cd server
pip install -r requirements.txt
uvicorn main:app --reload
```

### Testing

```bash
# Test the API
curl -X POST "http://localhost:8000/api/analyze-video" \
  -F "video=@your_video.mp4" \
  -F "query=Can you see my laptop?"
```
