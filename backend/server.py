from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path

# Import all routers
from app.routers import chat, vision, generation, history, gallery

# Create FastAPI app
app = FastAPI(title="Luna AI Backend API", version="1.0.0")

# CORS Middleware (Allows Frontend to talk to Backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, change this to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory (zaroori hai gallery images ke liye)
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Mount uploads directory 
# Isse frontend http://localhost:8000/uploads/image.jpg access kar payega
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include all routers with /api prefix
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(vision.router, prefix="/api", tags=["Vision"])
app.include_router(generation.router, prefix="/api", tags=["Generation"])
app.include_router(history.router, prefix="/api", tags=["History"])
app.include_router(gallery.router, prefix="/api", tags=["Gallery"])

@app.get("/")
def home():
    return {"message": "Luna AI Backend is Fully Operational! 🌕", "version": "1.0.0"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Luna AI"}

if __name__ == "__main__":
    import uvicorn
    # 👇 FIX: Changed port to 8000 to match Frontend .env
    uvicorn.run(app, host="0.0.0.0", port=8000)