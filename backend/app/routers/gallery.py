from fastapi import APIRouter, HTTPException, Query
from app.core.database import visual_memory_collection
from typing import Optional
import traceback

router = APIRouter()

@router.get("/gallery/{user_id}")
async def get_user_gallery(user_id: str, search: Optional[str] = Query(None)):
    """Get all images from visual memory with optional search"""
    try:
        # 1. Fetch ALL memories for user (Sync Call)
        # Local DB complex queries ($or, $regex) support nahi karta, 
        # isliye hum pehle sab data layenge fir Python mein filter karenge.
        cursor = visual_memory_collection.find({"user_id": user_id}).sort("timestamp", -1)
        all_memories = list(cursor)
        
        # 2. Manual Filtering (Python Logic instead of DB Logic)
        filtered_memories = []
        
        if search:
            search_lower = search.lower()
            for mem in all_memories:
                # Check description, tags, objects
                desc = mem.get("description", "") or ""
                tags = mem.get("tags", []) or []
                objects = mem.get("objects", []) or []
                
                in_desc = search_lower in desc.lower()
                in_tags = any(search_lower in t.lower() for t in tags)
                in_objs = any(search_lower in o.lower() for o in objects)
                
                if in_desc or in_tags or in_objs:
                    filtered_memories.append(mem)
        else:
            filtered_memories = all_memories

        # Limit to 100 most recent
        memories = filtered_memories[:100]
        
        # 3. Format response
        formatted_memories = []
        for mem in memories:
            formatted_memories.append({
                "id": str(mem.get("_id", "")), # Safety check
                # Support both image_url (URL) and image_path (Local File)
                "image_url": mem.get("image_url") or mem.get("image_path"),
                "description": mem.get("description"),
                "scene": mem.get("scene"),
                "objects": mem.get("objects", []),
                "mood": mem.get("mood"),
                "colors": mem.get("colors", []),
                "tags": mem.get("tags", []),
                "safety_score": mem.get("safety_score", 100),
                "memory_type": mem.get("memory_type"),
                "timestamp": str(mem.get("timestamp"))
            })
        
        return formatted_memories
    
    except Exception as e:
        print(f"Gallery Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gallery/{user_id}/stats")
async def get_gallery_stats(user_id: str):
    """Get statistics about user's gallery"""
    try:
        # 1. Fetch Data (Sync)
        cursor = visual_memory_collection.find({"user_id": user_id})
        memories = list(cursor)
        
        total = len(memories)
        
        # 2. Calculate Mood Distribution Manually 
        # (Kyunki Local DB 'aggregate' support nahi karta)
        mood_counts = {}
        for mem in memories:
            mood = mem.get("mood", "unknown")
            if mood:
                mood_counts[mood] = mood_counts.get(mood, 0) + 1
        
        # Convert to list format like MongoDB used to return
        mood_dist = [{"_id": k, "count": v} for k, v in mood_counts.items()]
        
        return {
            "total_images": total,
            "mood_distribution": mood_dist
        }
    
    except Exception as e:
        print(f"Stats Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))