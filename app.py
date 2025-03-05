import os
from dotenv import load_dotenv
from src.dashboard.app import create_app
from src.celery_app import celery_app

# Load environment variables
load_dotenv()

# Create the Flask application
app = create_app()

if __name__ == "__main__":
    # Run the Flask application
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 5001)),
        debug=os.getenv("DEBUG", "False").lower() == "true"
    ) 