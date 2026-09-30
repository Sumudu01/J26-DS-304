import uvicorn
import os
from app.main import app

# Hugging Face Spaces Gradio SDK expects the app to run on port 7860
port = int(os.environ.get("PORT", 7860))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)
