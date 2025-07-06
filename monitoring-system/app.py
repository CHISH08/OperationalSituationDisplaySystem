# app.py
import logging

# Configure logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logging.getLogger("src.retrieval").setLevel(logging.INFO)

import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from src import ImageQdrantIndexer, RemoteCLIP, ImageFolderCleaner

# Base directory
BASE_DIR = "./"

# Initialize components
embedder = RemoteCLIP(ckpt_path=os.path.join(BASE_DIR, "weights/RemoteCLIP-ViT-B-32.pt"))
cleaner = ImageFolderCleaner(deletion_threshold=60)
retriver = ImageQdrantIndexer(embedder, cleaner)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    text: str
    min_lat: Optional[float] = None
    max_lat: Optional[float] = None
    min_lon: Optional[float] = None
    max_lon: Optional[float] = None
    top_k: int = 5
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None

class SearchResult(BaseModel):
    image: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    score: float
    source: str
    date: Optional[List[int]] = None
    time: Optional[List[int]] = None

@app.post("/search", response_model=List[SearchResult])
async def search_images(request: SearchRequest):
    coord_range = None
    if all([request.min_lat, request.max_lat, request.min_lon, request.max_lon]):
        coord_range = (request.min_lat, request.max_lat, request.min_lon, request.max_lon)
    results = retriver.search(
        query=request.text,
        coord_range=coord_range,
        top_k=request.top_k,
        start_datetime=request.start_datetime,
        end_datetime=request.end_datetime
    )
    formatted = []
    for item in results:
        source = item['payload']['source']
        if source.startswith(BASE_DIR):
            rel = source[len(BASE_DIR):].lstrip('/')
            url = rel
        elif source.startswith("s3://"):
            bucket, key = source[5:].split('/', 1)
            url = f"https://storage.yandexcloud.net/{bucket}/{key}"
        else:
            url = source
        formatted.append(SearchResult(
            image=url,
            lat=item['payload'].get('lat'),
            lon=item['payload'].get('lon'),
            score=item['score'],
            source=url,
            date=item['payload'].get('date'),
            time=item['payload'].get('time')
        ))
    return formatted

@app.post("/process-folder")
async def process_folder(
    folder_path: str,
    batch_size: int = 16,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    background_tasks.add_task(retriver.process_image_folder, folder_path, batch_size)
    return {"status": "Processing started"}