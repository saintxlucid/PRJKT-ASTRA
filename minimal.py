from fastapi import FastAPI
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ASTRA Core is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    try:
        logger.info("Starting ASTRA Core API...")
        uvicorn.run(app, host="127.0.0.1", port=8088, log_config=None)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise