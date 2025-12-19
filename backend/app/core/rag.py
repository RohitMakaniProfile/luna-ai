from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

from app.core.database import visual_memory_collection
from datetime import datetime

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=api_key)

class GenerativeRAG:
    def __init__(self):
        self.client = client
        # ✅ Using stable model to prevent quota/version errors
        self.model_name = 'gemini-2.5-flash' 

    async def memorize_image(self, user_id: str, image_url: str, description: str, analysis: dict):
        """
        Save image memory to database with full analysis.
        """
        print(f"💾 RAG: Memorizing image for user {user_id}...")
        
        memory_doc = {
            "user_id": user_id,
            "image_url": image_url,
            "description": description,
            "scene": analysis.get('scene', ''),
            "objects": analysis.get('objects', []),
            "mood": analysis.get('mood', 'neutral'),
            "colors": analysis.get('colors', []),
            "tags": analysis.get('tags', []),
            "timestamp": datetime.utcnow()
        }
        
        # 👇 FIX 1: Removed 'await' (Local DB is synchronous)
        visual_memory_collection.insert_one(memory_doc)
        print("✅ RAG: Image memorized successfully.")

    async def retrieve_image(self, user_id: str, query: str):
        """
        Generative Search: Use Gemini to find the best matching image.
        """
        print(f"🔍 RAG: Searching for '{query}'...")

        # 1. Get all memories for this user
        # 👇 FIX 2: Removed 'await' and '.to_list()'
        # Local DB cursor is already a list-like object
        cursor = visual_memory_collection.find({"user_id": user_id})
        memories = list(cursor)
        
        if not memories:
            return None

        # 2. Prepare context for Gemini
        memory_text = ""
        for i, mem in enumerate(memories):
            desc = mem.get('description', 'Unknown')
            objects = ', '.join(mem.get('objects', []))
            mood = mem.get('mood', '')
            memory_text += f"ID: {i} | Description: {desc} | Objects: {objects} | Mood: {mood}\n"

        # 3. The "Selector" Prompt
        prompt = f"""
User Query: "{query}"

Available Images in Memory:
{memory_text}

Task: Identify the single best matching image ID.
If nothing matches well, return 'NONE'.
Return ONLY the ID number (e.g., '2').
"""

        try:
            # Using synchronous client call inside async wrapper is fine here
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            result = response.text.strip()
            
            print(f"🤖 RAG Decision: {result}")

            if result.isdigit():
                idx = int(result)
                if 0 <= idx < len(memories):
                    found_memory = memories[idx]
                    # Return URL or Path depending on what's stored
                    return found_memory.get('image_url') or found_memory.get('image_path')
        except Exception as e:
            print(f"⚠️ RAG Error: {e}")
        
        return None

# Singleton Instance
luna_rag = GenerativeRAG()