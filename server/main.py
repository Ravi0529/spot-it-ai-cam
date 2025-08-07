import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    pass


@app.get("/")
async def root():
    return {"message": "Hello from the server!"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
