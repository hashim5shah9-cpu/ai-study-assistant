import sys
import os

# Add current api directory to sys.path
api_dir = os.path.dirname(os.path.abspath(__file__))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

from main import app

try:
    from mangum import Mangum
    handler = Mangum(app)
except Exception:
    handler = app
