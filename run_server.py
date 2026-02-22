"""Entry point for the MediaProcessor FastAPI server."""

import uvicorn
from src.api import create_app

app = create_app(output_dir="./output", upload_dir="./uploads")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
