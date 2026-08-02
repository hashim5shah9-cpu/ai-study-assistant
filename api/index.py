import sys
import os
import traceback

# Add current api directory to sys.path
api_dir = os.path.dirname(os.path.abspath(__file__))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

try:
    from main import app
except Exception as init_error:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    
    error_traceback = traceback.format_exc()
    print(f"CRITICAL VERCEL INIT ERROR:\n{error_traceback}")
    
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
    async def vercel_error_handler(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Backend initialization exception on Vercel serverless runtime",
                "error": str(init_error),
                "traceback": error_traceback
            }
        )
