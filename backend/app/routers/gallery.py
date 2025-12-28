import traceback
import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from app.core.database import visual_memory_collection, generated_images_collection

router = APIRouter()

@router.get("/gallery/{user_id}")
async def get_user_gallery(user_id: str, search: Optional[str] = Query(None)):
    """विजुअल मेमोरी और लूना की बनाई फोटो, दोनों को एक साथ दिखाना"""
    try:
        # 1. दोनों कलेक्शन्स से डेटा लेना (Async तरीके से)
        v_cursor = visual_memory_collection.find({"user_id": user_id})
        g_cursor = generated_images_collection.find({"user_id": user_id})
        
        v_memories = list(v_cursor)
        g_memories = list(g_cursor)

        # 2. दोनों लिस्ट को एक साथ जोड़ना
        all_memories = v_memories + g_memories

        # 3. मैन्युअल सर्च फिल्टर (चूंकि लोकल DB regex सपोर्ट नहीं करता)
        filtered = []
        if search:
            s_lower = search.lower()
            for mem in all_memories:
                # अलग-अलग फील्ड्स में सर्च करना
                text_to_search = (
                    str(mem.get("description", "")) + 
                    str(mem.get("prompt", "")) + 
                    str(mem.get("scene", "")) + 
                    ",".join(mem.get("tags", []))
                ).lower()
                
                if s_lower in text_to_search:
                    filtered.append(mem)
        else:
            filtered = all_memories

        # 4. टाइमस्टैम्प के हिसाब से सॉर्ट करें (ताज़ा फोटो सबसे ऊपर)
        filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # 5. फ्रंटएंड (React) के लिए डेटा फॉर्मेट करना
        results = []
        for mem in filtered[:100]:
            results.append({
                "id": str(mem.get("_id")), # ID स्ट्रिंग में ज़रूरी है
                "image_url": mem.get("image_url") or mem.get("imageUrl") or mem.get("image_path"),
                "description": mem.get("description") or mem.get("prompt") or "Luna's Memory",
                "scene": mem.get("scene", ""),
                "mood": mem.get("mood", "neutral"),
                "tags": mem.get("tags", []),
                "timestamp": str(mem.get("timestamp"))
            })
        
        return results
    
    except Exception as e:
        print(f"❌ Gallery Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to load combined gallery")

@router.get("/gallery/{user_id}/stats")
async def get_gallery_stats(user_id: str):
    """गैलरी के आंकड़े प्राप्त करना"""
    try:
        v_memories = list(visual_memory_collection.find({"user_id": user_id}))
        g_memories = list(generated_images_collection.find({"user_id": user_id}))
        
        all_m = v_memories + g_memories
        mood_counts = {}
        for m in all_m:
            mood = m.get("mood", "unknown")
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
            
        return {
            "total_images": len(all_m),
            "visual_uploads": len(v_memories),
            "luna_creations": len(g_memories),
            "mood_distribution": [{"_id": k, "count": v} for k, v in mood_counts.items()]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
