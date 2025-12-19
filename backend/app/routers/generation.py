import os
import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google import genai
from app.core.database import generated_images_collection
# 👇 FIX 1: Correct file name (photo_engine)
from app.core.photoengine import select_companion_photo

import traceback

router = APIRouter()

# Setup Gemini for keyword extraction
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# ✅ Consistency: Using stable model
model_name = 'gemini-2.5-flash' 

class GenerationRequest(BaseModel):
    user_id: str
    prompt: str
    conversation_id: str | None = None

@router.post("/generate-luna")
async def generate_luna_photo(request: GenerationRequest):
    print(f"--- 🎨 GENERATING PHOTO FOR: {request.prompt} ---")
    
    try:
        # STEP 1: UNDERSTAND THE PROMPT
        extraction_prompt = f"""
Extract the main visual mood and a scene keyword from this prompt: "{request.prompt}"
Return string in format: MOOD,KEYWORD
Example: Happy,Coffee
"""
        
        result = client.models.generate_content(
            model=model_name,
            contents=extraction_prompt
        )
        text_result = result.text.strip()
        
        # Parse result (Default fallback if fails)
        mood = "neutral"
        keyword = "portrait"
        
        if "," in text_result:
            parts = text_result.split(",")
            mood = parts[0].strip().lower()
            keyword = parts[1].strip()

        # STEP 2: SELECT THE PHOTO
        photo_data = await select_companion_photo(mood, keyword)
        image_url = photo_data["url"]

        # STEP 3: SAVE TO LOCAL DB
        image_doc = {
            "user_id": request.user_id,
            "conversation_id": request.conversation_id,
            "prompt": request.prompt,
            "extracted_mood": mood,
            "extracted_keyword": keyword,
            "image_url": image_url,
            "caption": photo_data["caption"],
            "timestamp": datetime.datetime.utcnow()
        }
        
        # 👇 FIX 2: Removed 'await' (Local DB is synchronous)
        generated_images_collection.insert_one(image_doc)

        print(f"✅ Photo Generated: {image_url}")

        return {
            "imageUrl": image_url,
            "caption": photo_data["caption"],
            "mood": mood,
            "keyword": keyword,
            "status": "success"
        }

    except Exception as e:
        print(f"Generation Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/generated-images/{user_id}")
async def get_generated_images(user_id: str):
    """Get all generated images for a user"""
    try:
        # 👇 FIX 3: Removed 'await' and 'to_list'
        cursor = generated_images_collection.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(50)
        
        # Local DB cursor to list directly
        images = list(cursor)
        
        # Format response
        formatted_images = []
        for img in images:
            formatted_images.append({
                "id": str(img.get("_id", "")),
                "prompt": img.get("prompt"),
                "image_url": img.get("image_url"),
                "caption": img.get("caption"),
                "mood": img.get("extracted_mood"),
                "keyword": img.get("extracted_keyword"),
                "timestamp": str(img.get("timestamp"))
            })
        
        return formatted_images
    
    except Exception as e:
        print(f"Fetch Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))