import datetime
import os
import asyncio
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate

# ✅ Correct Imports
from app.core.database import conversations_collection, visual_memory_collection
from app.core.personality import LUNA_SYSTEM_PROMPT
from app.core.rag import luna_rag
from app.core.photoengine import select_companion_photo 
# Note: Ensure file is named photo_engine.py, not photoengine

# --- 1. DEFINE STATE ---
class AgentState(TypedDict):
    user_id: str
    user_message: str
    image_analysis: Optional[dict]
    intent: str
    mood: str
    photo_subject: Optional[str]
    context_summary: str
    chat_history: List[dict]
    final_response: str
    photo_url: Optional[str]

# --- 2. SETUP LLM ---
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", # ✅ Changed to stable model (2.0-exp might cause errors)
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.7,
    max_retries=3,
)

# --- 3. DEFINE NODES ---

async def node_retrieve_context(state: AgentState):
    print(f"--- 🧠 NODE: RETRIEVING CONTEXT FOR {state['user_id']} ---")
    user_id = state['user_id']
    
    # 👇 FIX 1: Removed 'await' and '.to_list()'
    # Local DB returns a list directly
    history_cursor = conversations_collection.find({"user_id": user_id}).sort("timestamp", 1).limit(10)
    history_docs = list(history_cursor) 

    mem_cursor = visual_memory_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(5)
    memories = list(mem_cursor)

    context_str = ""
    if memories:
        context_str += "\n\n**Visual Memories:**\n"
        for mem in memories:
            desc = mem.get('description', 'unknown image')
            context_str += f"- {desc}\n"

    return {"context_summary": context_str, "chat_history": history_docs}

async def node_analyze_intent(state: AgentState):
    print("--- 🕵️ NODE: ANALYZING INTENT & SUBJECT ---")
    try:
        prompt = PromptTemplate.from_template(
            "Analyze this message: '{message}'. "
            "1. Does the user want a photo/image? "
            "2. If YES, what is the main VISUAL SUBJECT? (Extract 1-2 words only, e.g., 'girl', 'coffee cup', 'rainy city'). "
            "Return JSON: {{'intent': 'photo' or 'chat', 'mood': 'neutral/happy/sad', 'subject': '...'}}"
        )
        chain = prompt | llm
        response = await chain.ainvoke({"message": state['user_message']})
        import json
        txt = response.content.replace("```json", "").replace("```", "")
        result = json.loads(txt)
        
        subject = result.get("subject") or state['user_message']
        
        return {
            "intent": result.get("intent", "chat"),
            "mood": result.get("mood", "neutral"),
            "photo_subject": subject
        }
    except Exception as e:
        print(f"⚠️ Intent Error: {e}")
        return {"intent": "chat", "mood": "neutral", "photo_subject": None}

async def node_select_photo(state: AgentState):
    print("--- 📸 NODE: SELECTING PHOTO ---")
    user_id = state['user_id']
    
    query = state.get('photo_subject') or state['user_message']
    print(f"🔍 Searching for: '{query}'")

    try:
        # Try to retrieve from personal memories first (RAG might still be async)
        personal_photo = await luna_rag.retrieve_image(user_id, query)
        if personal_photo:
            return {"photo_url": personal_photo, "final_response": "I found this memory! 📸"}

        # Generate/select a companion photo
        photo_data = await select_companion_photo(state.get("mood", "happy"), query)
        return {"photo_url": photo_data["url"], "final_response": photo_data["caption"]}
    except Exception as e:
        print(f"Photo Error: {e}")
        return {"final_response": "Camera glitch! Can't send photo right now."}

async def node_generate_reply(state: AgentState):
    print("--- 💬 NODE: GENERATING REPLY ---")
    if state.get("final_response"): 
        return {}

    try:
        full_system_prompt = LUNA_SYSTEM_PROMPT + state.get('context_summary', "")
        messages = [SystemMessage(content=full_system_prompt)]

        for doc in state.get('chat_history', []):
            content = doc.get('content', "")
            if doc.get('role') == 'user': 
                messages.append(HumanMessage(content=content))
            else: 
                messages.append(AIMessage(content=content))

        current_content = state['user_message']
        if state.get('image_analysis'):
            current_content += f"\n[Image Context: {state['image_analysis'].get('description', '')}]"
        
        messages.append(HumanMessage(content=current_content))
        response = await llm.ainvoke(messages)
        return {"final_response": response.content}

    except Exception as e:
        print(f"⚠️ LLM Error: {e}")
        return {"final_response": "My connection is fluctuating. Let's wait a moment! ✨"}

async def node_save_interaction(state: AgentState):
    print("--- 💾 NODE: SAVING TO DB ---")
    user_id = state['user_id']
    timestamp = datetime.datetime.utcnow()

    # 👇 FIX 2: Removed 'await' here because Local DB is Sync
    conversations_collection.insert_one({
        "user_id": user_id, 
        "role": "user",
        "content": state['user_message'], 
        "timestamp": timestamp
    })
    
    conversations_collection.insert_one({
        "user_id": user_id, 
        "role": "assistant",
        "content": state['final_response'], 
        "photo_sent": state.get('photo_url'),
        "timestamp": timestamp
    })
    return {}

# --- 4. BUILD GRAPH ---
workflow = StateGraph(AgentState)
workflow.add_node("retrieve", node_retrieve_context)
workflow.add_node("analyze", node_analyze_intent)
workflow.add_node("photo", node_select_photo)
workflow.add_node("chat", node_generate_reply)
workflow.add_node("save", node_save_interaction)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "analyze")

def route_intent(state): 
    return "photo" if state["intent"] == "photo" else "chat"

workflow.add_conditional_edges("analyze", route_intent, {"photo": "photo", "chat": "chat"})

workflow.add_edge("photo", "save")
workflow.add_edge("chat", "save")
workflow.add_edge("save", END)

graph = workflow.compile()

# --- 5. WRAPPER CLASS ---
class LunaAgentWrapper:
    def __init__(self, graph):
        self.graph = graph

    async def process_message(self, user_id, message, image_analysis=None, history=None):
        initial_state = {
            "user_id": user_id,
            "user_message": message or "",
            "image_analysis": image_analysis,
            "chat_history": history or [],
            "intent": "chat",
            "mood": "neutral",
            "photo_subject": None,
            "context_summary": "",
            "final_response": "",
            "photo_url": None
        }
        result = await self.graph.ainvoke(initial_state)
        return {
            "reply": result.get("final_response"),
            "photo_url": result.get("photo_url")
        }

luna_agent = LunaAgentWrapper(graph)