import os
import json
import datetime
import re
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.database import visual_memory_collection

# --- 1. CONFIGURATION ---
DISALLOWED_PATTERNS = [
    'nudity', 'nude', 'naked', 'nsfw', 'explicit',
    'violence', 'violent', 'blood', 'gore', 'weapon', 'gun', 'knife',
    'illegal', 'drug', 'substance',
    'self-harm', 'suicide', 'cutting'
]

# --- 2. DEFINE STATE ---
class VisionState(TypedDict):
    user_id: str
    image_base64: str
    image_url: Optional[str]
    raw_analysis_text: str
    parsed_analysis: Dict[str, Any]
    is_safe: bool
    safety_issues: List[str]
    memory_type: str
    status: str

# --- 3. SETUP MODEL ---
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.8 # Thoda creative hone ke liye badhaya
)

# --- 4. DEFINE NODES ---

async def node_analyze_image(state: VisionState):
    print("--- 👁️ NODE: GEMINI VISION ANALYSIS ---")
    
    # 👇 UPDATED PROMPT: Ab yeh 'Reaction' + 'Question' generate karega
    prompt = """
You are Abhay (or Luna), a cool, witty, intelligent best friend from Delhi. 
Analyze this image and return a valid JSON response.

IMPORTANT: In the 'comment' field, DO NOT just describe the image. 
Instead, REACT to it in Hinglish (Hindi+English mix) or casual English and ASK a relevant question to start a conversation.

Examples:
- (Image of Safari/Animals) -> "Oye hoye! Jungle safari? Sher dikha kya ya bas hiran dekh ke aa gaye?"
- (Image of Food) -> "Bhai gazab! Akele akele pizza party? Muje nahi bulaya?"
- (Image of Laptop/Code) -> "Raat bhar coding? Project deadline hai kya bro?"
- (Image of Sunset) -> "Uff, kya view hai! Kaha ghumne gaye ho?"

OUTPUT RAW JSON ONLY. NO MARKDOWN. NO BACKTICKS.
{
    "comment": "Your interactive Hinglish reaction + question here",
    "scene": "Short technical description in English for database search",
    "objects": ["obj1", "obj2"],
    "mood": "mood",
    "tags": ["tag1", "tag2"],
    "safety_concerns": "none"
}
"""

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{state['image_base64']}"}
            }
        ]
    )

    try:
        response = await llm.ainvoke([message])
        # print(f"🔹 RAW AI RESPONSE: {response.content}") # Debugging ke liye remove comment
        return {"raw_analysis_text": response.content}
    except Exception as e:
        print(f"❌ Vision API Error: {e}")
        return {"raw_analysis_text": "Error in AI generation", "status": "error"}

def node_process_safety(state: VisionState):
    print("--- 🛡️ NODE: SAFETY & PROCESSING ---")
    text = state.get('raw_analysis_text', "")
    
    analysis = {}
    
    # 👇 ROBUST JSON PARSING (Taki fallback msg kam aaye)
    try:
        # 1. Clean Markdown backticks if present
        clean_text = re.sub(r'```json\s*', '', text)
        clean_text = re.sub(r'```', '', clean_text).strip()
        
        # 2. Extract JSON using Regex (Sabse safe tarika)
        json_match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if json_match:
            clean_text = json_match.group(0)
            
        analysis = json.loads(clean_text)
        
    except Exception as e:
        print(f"⚠️ JSON Parsing Failed: {e}")
        print(f"⚠️ Falling back to Raw Text")
        
        # Agar JSON fail ho jaye, to pura text hi 'comment' maan lo
        # Taki 'Wow interesting shot' na dikhana pade
        analysis = {
            "comment": text if text else "Arre photo load nahi hui theek se, dobara bhejo!",
            "scene": "Image analysis",
            "objects": [],
            "mood": "Neutral",
            "tags": [],
            "safety_concerns": "none"
        }

    # Keyword Safety Check
    issues = []
    raw_str = str(analysis).lower()
    for pattern in DISALLOWED_PATTERNS:
        if pattern in raw_str:
            issues.append(pattern)
            
    is_safe = len(issues) == 0
    safety_score = 100 if is_safe else 0
    analysis['safety_score'] = safety_score
    
    # Memory Type Logic
    mem_type = 'visual'
    objects = [obj.lower() for obj in analysis.get('objects', [])]
    scene = analysis.get('scene', '').lower()
    
    if any(x in str(objects) for x in ['person', 'people', 'man', 'woman', 'child', 'friends']):
        mem_type = 'relationship'
    elif 'location' in scene or 'place' in scene or 'outdoor' in scene:
        mem_type = 'location'
    elif len(objects) > 0:
        mem_type = 'object'

    return {
        "parsed_analysis": analysis,
        "is_safe": is_safe,
        "safety_issues": issues,
        "memory_type": mem_type
    }

async def node_save_memory(state: VisionState):
    # Sirf tab save karein agar image safe thi
    if state['is_safe']:
        print("--- 💾 SAVING MEMORY ---")
        doc = {
            "user_id": state['user_id'],
            "image_url": state.get('image_url', ''),
            "type": "visual_memory",
            "memory_type": state['memory_type'],
            "description": state['parsed_analysis'].get('scene'), # Database ke liye English description
            "luna_comment": state['parsed_analysis'].get('comment'), # Luna ka reaction
            "mood": state['parsed_analysis'].get('mood'),
            "objects": state['parsed_analysis'].get('objects', []),
            "tags": state['parsed_analysis'].get('tags', []),
            "safety_score": state['parsed_analysis'].get('safety_score', 100),
            "timestamp": datetime.datetime.utcnow()
        }
        visual_memory_collection.insert_one(doc)
        return {"status": "saved"}
    else:
         return {"status": "blocked"}

# --- 5. BUILD GRAPH ---
def route_safety(state: VisionState):
    if state['is_safe']:
        return "save"
    return "end"

workflow = StateGraph(VisionState)
workflow.add_node("see", node_analyze_image)
workflow.add_node("think", node_process_safety)
workflow.add_node("save", node_save_memory)

workflow.set_entry_point("see")
workflow.add_edge("see", "think")
workflow.add_conditional_edges("think", route_safety, {"save": "save", "end": END})
workflow.add_edge("save", END)

vision_agent = workflow.compile()