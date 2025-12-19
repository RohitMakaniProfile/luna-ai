from fastapi import APIRouter, UploadFile, File, HTTPException, Form
import base64
import os
import shutil
import uuid
# ✅ Fixed Import
from app.core.vision_agent import vision_agent
from app.core.rag import luna_rag

router = APIRouter()

# Uploads directory setup
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/analyze-image")
async def analyze_image(user_id: str = Form(...), file: UploadFile = File(...)):
    try:
        print(f"--- 📸 ANALYZING IMAGE FOR: {user_id} ---")
        
        # 1. Generate unique filename & Save to Disk
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as buffer:
            # File read karo
            content = await file.read()
            buffer.write(content)
            
        # 2. Convert to Base64 (For AI Agent)
        image_b64 = base64.b64encode(content).decode("utf-8")
        
        # 3. Define Image URL/Path (For Database/Gallery)
        # Hum file path save karenge taaki gallery isse load kar sake
        image_url = file_path 

        # 4. Run the Vision Agent
        initial_state = {
            "user_id": user_id,
            "image_base64": image_b64,
            "image_url": image_url,
            "raw_analysis_text": "",
            "parsed_analysis": {},
            "is_safe": True,
            "safety_issues": [],
            "memory_type": "unknown",
            "status": "processing"
        }

        result = await vision_agent.ainvoke(initial_state)

        # 5. Extract Analysis
        analysis = result.get("parsed_analysis", {})
        
        # 6. Save to RAG memory
        # Note: luna_rag.memorize_image 'async' hai, isliye await sahi hai
        if result.get("is_safe"):
            await luna_rag.memorize_image(
                user_id=user_id,
                image_url=image_url,
                description=analysis.get("scene", "Unknown image"),
                analysis=analysis
            )

        return {
            "analysis": analysis,
            "status": result.get("status", "success"),
            "is_safe": result.get("is_safe", True),
            "safety_issues": result.get("safety_issues", [])
        }

    except Exception as e:
        print(f"❌ Vision Router Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))