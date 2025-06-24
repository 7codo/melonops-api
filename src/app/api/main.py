from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.lib.config import get_settings
import logging
import sys
import uvicorn
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

origins = ["http://localhost:3000"]

settings = get_settings()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Health check."""
    logger.debug("Health check endpoint called")
    return {"status": "ok"}


# For dev env
def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.api.main:app",  # the path to your FastAPI file, replace this if its different
        host="0.0.0.0",
        port=port,
    )


if __name__ == "__main__":
    main()
