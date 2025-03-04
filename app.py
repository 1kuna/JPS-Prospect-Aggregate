import os
from dotenv import load_dotenv
from src.dashboard.app import create_app
from src.scheduler.scheduler import start_scheduler

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Start the scheduler in the background
    start_scheduler()
    
    # Create and run the Flask application
    app = create_app()
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("DEBUG", "False").lower() == "true"
    ) 