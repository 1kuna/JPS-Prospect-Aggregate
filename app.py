import os
from dotenv import load_dotenv
from src.dashboard.app import create_app
from src.celery_app import celery_app

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Create and run the Flask application
    app = create_app()
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("DEBUG", "False").lower() == "true"
    ) 