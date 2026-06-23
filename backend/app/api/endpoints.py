from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import List, Optional
from pydantic import BaseModel
from app.core.rag import process_files, chat_with_rag
import traceback

router = APIRouter()

class ChatResponse(BaseModel):
    answer: str

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    question: str = Form(...),
    model: str = Form("deepseek"),
    files: List[UploadFile] = File(None)
):
    try:
        # If files are provided, process them first (append mode)
        if files:
            print(f"Chat request includes {len(files)} files. Processing...")
            await process_files(files, mode="append")

        answer = await chat_with_rag(question, model)
        if hasattr(answer, 'content'):
            return ChatResponse(answer=answer.content)
        return ChatResponse(answer=str(answer))
    except Exception as e:
        print(f"Chat Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    mode: str = Form("append")
):
    try:
        print(f"Received upload request. Files: {len(files)}, Mode: {mode}")
        result = await process_files(files, mode)
        return {"message": result}
    except Exception as e:
        print(f"Upload Error: {e}")
        traceback.print_exc()
        # Return detailed error to client for easier debugging
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
