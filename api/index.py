"""Single Vercel Function entrypoint for the FastAPI API.

The frontend and API live in the same Vercel project.  Keeping the API local
to this deployment avoids proxying an API request to a hostname that resolves
back through this project's rewrites (which produces Vercel's HTTP 508).
"""

from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
