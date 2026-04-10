# run.py
# Entry point — run from project root: python run.py

import uvicorn

from src.core.settings import SERVER_HOST, SERVER_PORT, SERVER_RELOAD

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=SERVER_RELOAD,
    )
