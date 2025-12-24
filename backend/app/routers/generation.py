import os
import datetime
import random
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google import genai
from app.core.database import generated_images_collection
# ✅ Correct Import
from app.core.photoengine import select_companion_photo

router = APIRouter()

# Setup Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
model_name = 'gemini-2.5-flash' 

# --- 🌟 SECTION 1: DYNAMIC VARIABLES (Randomness) ---
# हर बार अलग समय और कपड़े, ताकि फोटो रिपीट न हो
TIME_OF_DAY = [
    "during golden hour with warm sunlight", 
    "in soft overcast morning light", 
    "under moody cinematic streetlights", 
    "on a bright sunny afternoon", 
    "in dramatic window lighting"
]

CAMERA_ANGLES = [
    "candid shot looking slightly away", 
    "intense close-up portrait focusing on eyes", 
    "wide angle lifestyle shot", 
    "side profile view", 
    "eye-level natural shot"
]

CLOTHING_STYLES = [
    "wearing a textured wool sweater", 
    "wearing a casual cotton t-shirt", 
    "wearing a denim jacket over a white tee", 
    "wearing a white linen shirt", 
    "wearing a vintage leather jacket"
]

# --- 🌟 SECTION 2: MASTER REALISM BOOSTERS (The Secret Sauce) ---
# 👇 यह ब्लॉक फोटो को "AI" से "Photography" में बदल देता है
REALISM_TAGS = (
    "cinematic candid portrait, shot on Sony A7R V, 85mm f/1.2 GM lens, "
    "extremely shallow depth of field, creamy bokeh background, "
    "highly detailed natural skin texture with visible pores, slight skin imperfections, "
    "soft cinematic lighting, moody atmosphere, natural film grain, "
    "raw unedited photo style, Kodak Portra 400 film look, 8k uhd, hyper-realistic, masterpiece"
)

# 👇 नेगेटिव प्रॉम्प्ट: यह AI को सख्त मना करता है कि कार्टून न बनाए
NEGATIVE_HINTS = (
    " --no cartoon, 3d render, illustration, painting, smooth plastic skin, "
    "anime, drawing, bad anatomy, disfigured, makeup overdose, "
    "oversaturated, blurry details, low resolution, artificial look"
)

class GenerationRequest(BaseModel):
    user_id: str
    prompt: str
    conversation_id: str | None = None

# --- 🌟 HELPER FUNCTION ---
# ... Imports same rahenge

def build_enhanced_prompt(base_topic):
    """
    Combines User Topic + Luna's Persona (ALWAYS FEMALE)
    """
    
    # 🌟 FORCE LUNA PERSONA
    # Agar user ne specifically 'boy' ya 'man' nahi likha, to hamesha Luna (Girl) add karo
    if "man" not in base_topic.lower() and "boy" not in base_topic.lower():
        base_topic = f"A beautiful young indian woman with wavy hair, {base_topic}"

    time = random.choice(TIME_OF_DAY)
    angle = random.choice(CAMERA_ANGLES)
    cloth = random.choice(CLOTHING_STYLES)
    
    # Final Formula
    return f"{base_topic}, {cloth}, {time}, {angle}, {REALISM_TAGS}{NEGATIVE_HINTS}"
@router.post("/generate-luna")
async def generate_luna_photo(request: GenerationRequest):
    print(f"--- 🎨 GENERATING MASTERPIECE FOR: {request.prompt} ---")
    
    try:
        # STEP 1: EXTRACT THE CORE SUBJECT (Gemini)
        # हम Gemini से सिर्फ 'Keyword' नहीं, बल्कि 'Visual Description' मांग रहे हैं
        extraction_prompt = f"""
Analyze this user request: "{request.prompt}"
Extract the main visual subject performing an action.
Ignore emotional words. 
Return ONLY the subject string. 
Example Input: "I want to see her drinking coffee happily"
Example Output: "A young woman drinking coffee from a ceramic mug"
"""
        result = client.models.generate_content(
            model=model_name,
            contents=extraction_prompt
        )
        visual_subject = result.text.strip()
        
        # Safety fallback
        if not visual_subject or len(visual_subject) < 3:
            visual_subject = request.prompt

        # STEP 2: APPLY THE REALISM FORMULA
        enhanced_prompt = build_enhanced_prompt(visual_subject)
        print(f"✨ Enhanced Prompt: {enhanced_prompt}")

        # STEP 3: GENERATE PHOTO
        # Note: Mood hum 'neutral' bhej rahe hain kyunki saara style prompt handle karega
        photo_data = await select_companion_photo("neutral", enhanced_prompt)
        image_url = photo_data["url"]

        # STEP 4: SAVE TO DB
        image_doc = {
            "user_id": request.user_id,
            "conversation_id": request.conversation_id,
            "prompt": request.prompt,
            "enhanced_prompt": enhanced_prompt, # Debugging ke liye save kar rahe hain
            "image_url": image_url,
            "caption": photo_data["caption"],
            "timestamp": datetime.datetime.utcnow()
        }
        
        # Local DB insert (Synchronous)
        generated_images_collection.insert_one(image_doc)

        print(f"✅ Photo Generated: {image_url}")

        return {
            "imageUrl": image_url,
            "caption": photo_data["caption"],
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
        cursor = generated_images_collection.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(50)
        
        images = list(cursor)
        
        formatted_images = []
        for img in images:
            formatted_images.append({
                "id": str(img.get("_id", "")),
                "prompt": img.get("prompt"),
                "image_url": img.get("image_url"),
                "caption": img.get("caption"),
                "timestamp": str(img.get("timestamp"))
            })
        
        return formatted_images
    
    except Exception as e:
        print(f"Fetch Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
