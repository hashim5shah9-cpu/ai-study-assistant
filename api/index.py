import sys
import os

# Add root directory and backend directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
backend_dir = os.path.join(parent_dir, 'backend')

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from backend.main import app
except Exception as err:
    # If any error occurs during import, serve a fallback FastAPI app so Vercel does not crash with 500
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/{full_path:path}")
    @app.post("/{full_path:path}")
    async def catch_all_error(full_path: str):
        return {
            "status": "error",
            "message": "Backend initialization exception",
            "details": str(err)
        }
