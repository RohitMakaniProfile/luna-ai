from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.core.agent import luna_agent
from app.core.database import conversations_collection
import traceback

router = APIRouter()

class ChatRequest(BaseModel):
    user_id: str
    message: Optional[str] = None
    imageAnalysis: Optional[Dict[str, Any]] = None

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        print(f"--- 🧠 CHAT REQUEST FROM: {request.user_id} ---")

        # Load conversation history
        # 👇 FIX: await aur .to_list() hataya (Local DB ke liye)
        history_cursor = conversations_collection.find(
            {"user_id": request.user_id}
        ).sort("timestamp", 1).limit(15)
        
        # Local DB cursor seedha list mein convert ho jata hai
        history = list(history_cursor)

        # Process message through agent
        response_data = await luna_agent.process_message(
            user_id=request.user_id,
            message=request.message,
            image_analysis=request.imageAnalysis,
            history=history
        )

        return response_data

    except Exception as e:
        print(f"Chat Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))