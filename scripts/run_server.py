import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import uvicorn

if __name__ == "__main__":
    os.environ["ALLOW_SQLITE_FALLBACK"] = "true"
    if not os.getenv("POSTGRES_PASSWORD"):
        os.environ["USE_DATABASE_BACKEND"] = "false"
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, log_level="info")
