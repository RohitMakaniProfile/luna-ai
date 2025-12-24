import os
import random
import asyncio
import urllib.parse
from google import genai

# --- 1. SETUP GEMINI (For Smart Captions) ---
# Ensure GEMINI_API_KEY is set in your environment variables
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
model_name = 'gemini-2.5-flash'

async def generate_smart_caption(prompt: str, mood: str) -> str:
    """
    Generates a caption relevant to the photo action.
    """
    try:
        # Gemini ko bolte hain ki photo ke action par comment kare
        caption_prompt = f"""
        You are Luna. You just sent a photo of: "{prompt}".
        
        Write a 1-line Hinglish caption acting like you are IN the photo.
        
        - If prompt has 'working': say something like "Deadline ka pressure! 🤯"
        - If prompt has 'coffee': say "Chai-Coffee break zaroori hai. ☕"
        - Keep it under 10 words. Don't be generic.
        """
        
        response = client.models.generate_content(
            model=model_name,
            contents=caption_prompt
        )
        return response.text.strip()
    except Exception as e:
        return "Ye lo! ✨"
async def select_companion_photo(mood: str, prompt: str = None) -> dict:
    """
    Selects a photo based on mood and the ENHANCED prompt from generation.py.
    """
    
    # --- 2. BACKUP COLLECTION (Unsplash - Fallback only) ---
    base_url = "https://images.unsplash.com/photo-"
    
    collections = {
        "happy": ["1514888286974-6c03e2ca1dba", "1502920917128-1aa500764cbd"],
        "sad": ["1516550893723-fab71cc96e50", "1494368308039-ed3393a7eb28"],
        "romantic": ["1518199266791-5375a83190b7", "1529333446548-aaef567d8cd1"],
        "nature": ["1501854140884-074cf2b2c3af", "1470071459604-3b5ec3a7fe05"],
        "neutral": ["1509042239860-f550ce710b93", "1486312338219-ce68d2c6f44d"]
    }
    
    # --- 3. GENERATION LOGIC (Pollinations AI) ---
    final_url = ""
    smart_caption = ""
    
    # Agar generation.py se 'enhanced_prompt' aaya hai
    if prompt and len(prompt) > 5:
        
        # URL Encode (Spaces ko %20 me badalna)
        encoded_prompt = urllib.parse.quote(prompt)
        
        # ✨ IMPROVEMENT: Using 'flux' model for Realism
        # Random seed ensure karta hai ki har baar nayi photo bane
        seed = random.randint(1, 99999)
        final_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={seed}&model=flux"
        
        # ✨ IMPROVEMENT: Generating Smart Caption
        smart_caption = await generate_smart_caption(prompt, mood)
        
    else:
        # Step B: Fallback (Unsplash) if no prompt provided
        selected_category = mood if mood in collections else "neutral"
        ids = collections[selected_category]
        selected_id = random.choice(ids)
        final_url = f"{base_url}{selected_id}?w=800&q=80"
        smart_caption = "Here is a random click for you! 📸"

    # Network simulation (Thoda realistic pause)
    await asyncio.sleep(0.5)

    return {
        "url": final_url,
        "caption": smart_caption
    }
