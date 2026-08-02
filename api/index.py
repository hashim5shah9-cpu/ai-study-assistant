import sys
import os
import traceback

# Initialize app placeholder at the top level for Vercel's static AST analyzer
app = None

# Add api directory to sys.path
api_dir = os.path.dirname(os.path.abspath(__file__))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

try:
    from main import app as real_app
    app = real_app
except BaseException as err:
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
    
    error_traceback = traceback.format_exc()
    
    @app.get("/{full_path:path}")
    @app.post("/{full_path:path}")
    async def catch_all_error(full_path: str):
        return {
            "status": "error",
            "message": "Backend initialization exception at runtime",
            "error_class": err.__class__.__name__,
            "error_message": str(err),
            "traceback": error_traceback
        }
