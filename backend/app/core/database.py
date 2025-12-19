import os
import json
import datetime
from typing import List, Optional

# ✅ Using Local DB Logic
USE_LOCAL_DB = True 

class LocalFileDB:
    def __init__(self, filename="luna_memory.json"):
        self.filename = filename
        self._ensure_file()

    def _ensure_file(self):
        # Agar file nahi hai to banayein aur empty structure likhein
        if not os.path.exists(self.filename):
            with open(self.filename, "w") as f:
                json.dump({
                    "conversations": [], 
                    "visual_memories": [], 
                    "generated_images": [], # 👈 Yeh zaroori tha
                    "users": []
                }, f)

    def _read_data(self):
        try:
            with open(self.filename, "r") as f:
                return json.load(f)
        except:
            return {"conversations": [], "visual_memories": [], "generated_images": [], "users": []}

    def _write_data(self, data):
        with open(self.filename, "w") as f:
            json.dump(data, f, indent=2, default=str)

    # --- Pseudo-MongoDB Properties ---
    
    @property
    def conversations(self): return self._Collection(self, "conversations")
    
    @property
    def visual_memories(self): return self._Collection(self, "visual_memories")
    
    # 👇 THIS WAS MISSING (Ab add kar diya hai)
    @property
    def generated_images(self): return self._Collection(self, "generated_images")

    # --- Mock Collection Class ---
    class _Collection:
        def __init__(self, db_instance, name):
            self.db = db_instance
            self.name = name

        def find(self, query=None):
            data = self.db._read_data()
            rows = data.get(self.name, [])
            
            # Simple User ID Filter
            if query and "user_id" in query:
                rows = [r for r in rows if r.get("user_id") == query["user_id"]]
            
            # Sort & Limit Mock (chaining methods)
            class Cursor(list):
                def sort(self, key, direction=1):
                    try:
                        self.sort(key=lambda x: x.get(key, ""), reverse=(direction == -1))
                    except: pass
                    return self
                def limit(self, n):
                    return self[:n]

            return Cursor(rows)

        def insert_one(self, doc):
            data = self.db._read_data()
            if self.name not in data: data[self.name] = []
            
            # Fix Datetime for JSON
            if "timestamp" in doc and isinstance(doc["timestamp"], datetime.datetime):
                doc["timestamp"] = doc["timestamp"].isoformat()
                
            data[self.name].append(doc)
            self.db._write_data(data)
            return True

# --- EXPORT VARIABLES ---
print("✅ Using Local File Database (Fixed with Generated Images)")
db = LocalFileDB()

# Export Collections
conversations_collection = db.conversations
visual_memory_collection = db.visual_memories
generated_images_collection = db.generated_images # 👈 Fixed Import Error
users_collection = None