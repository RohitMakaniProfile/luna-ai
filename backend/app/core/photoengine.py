import random
import asyncio
import urllib.parse

async def select_companion_photo(mood: str, scene_keyword: str = None) -> dict:
    """
    Selects a photo based on mood and keyword.
    Uses Pollinations AI for generation with PRO prompts,
    and falls back to a large collection of Unsplash images.
    """
    
    # --- 1. BACKUP COLLECTION (High-quality Unsplash photos) ---
    base_url = "https://images.unsplash.com/photo-"
    
    collections = {
        "happy": [
            "1514888286974-6c03e2ca1dba",  # Happy girl
            "1502920917128-1aa500764cbd",  # Jumping in joy
            "1516726817592-8e005af99156",  # Cozy coffee
            "1531747056595-07f6cbbe10fd",  # Laughter
            "1523240795612-9a054b0db644"   # Friends laughing
        ],
        "sad": [
            "1516550893723-fab71cc96e50",  # Rain window
            "1494368308039-ed3393a7eb28",  # Lonely beach
            "1518020382338-a7de69f8bf40",  # Sad mood lighting
            "1466093065054-e6429bc9eb9e",  # Alone in forest
            "1453227588063-bb30fd97a025"   # Grey clouds
        ],
        "romantic": [
            "1518199266791-5375a83190b7",  # Holding hands
            "1529333446548-aaef567d8cd1",  # Couple sunset
            "1516589178581-6cd7833ae3b2",  # Love heart
            "1474552226712-ac0f0961a954"   # Rose
        ],
        "nature": [
            "1501854140884-074cf2b2c3af",  # Forest
            "1470071459604-3b5ec3a7fe05",  # Mountains
            "1441974231531-c6227db76b6e"   # Sunlight trees
        ],
        "neutral": [
            "1509042239860-f550ce710b93",  # Coffee cup
            "1486312338219-ce68d2c6f44d",  # Macbook writing
            "1499750310159-5b5f336a3983"   # Clean desk
        ]
    }
    
    # --- 2. GENERATION LOGIC (Best Prompts) ---
    final_url = ""
    
    if scene_keyword and len(scene_keyword) > 2:
        # Step A: Prompt Enhancement (Magic Words)
        base_prompt = scene_keyword
        
        # If user mentions "me" or "girl", show a consistent character
        if "girl" in base_prompt.lower() or "me" in base_prompt.lower() or "selfie" in base_prompt.lower():
            character_style = "beautiful girl with indian features, black hair, warm smile, futuristic cosmic vibe"
            base_prompt = base_prompt.replace("girl", character_style).replace("me", character_style)
            
        # Magic Suffix (Improves quality 10x)
        modifiers = ", cinematic lighting, 8k resolution, photorealistic, highly detailed, shot on 35mm lens, bokeh effect, masterpiece"
        
        full_prompt = base_prompt + modifiers
        
        # URL Encode (Convert spaces to %20)
        encoded_prompt = urllib.parse.quote(full_prompt)
        
        # Pollinations AI URL
        final_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=600&nologo=true&seed={random.randint(1, 10000)}"
        
    else:
        # Step B: Fallback (Unsplash)
        selected_category = mood if mood in collections else "neutral"
        ids = collections[selected_category]
        selected_id = random.choice(ids)
        final_url = f"{base_url}{selected_id}?w=800&q=80"

    # --- 3. CAPTIONS ---
    captions = [
        "Here is what you asked for! 📸",
        "I thought you might like this view. ✨",
        "Capturing the moment just for you...",
        "Look what I found in the cosmic gallery! 🌌",
        "Sending this with positive vibes. 💫"
    ]
    
    # Network simulation
    await asyncio.sleep(0.1)

    return {
        "url": final_url,
        "caption": random.choice(captions)
    }
