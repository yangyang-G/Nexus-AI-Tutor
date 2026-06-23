from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as api_router
from app.core.rag import get_vector_store
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Nexus AI Tutor API")

# CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:80",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    # Initialize vector store on startup
    get_vector_store()

@app.get("/")
async def root():
    return {"message": "Nexus AI Tutor Backend Running"}
