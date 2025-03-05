#!/bin/bash

echo "Setting up JPS Proposal Forecast Aggregator..."

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "Conda is not installed. Please install Miniconda or Anaconda first."
    echo "You can download it from: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Create conda environment
echo "Creating conda environment..."
conda create -n jps_env python=3.12 -y

# Activate conda environment
echo "Activating conda environment..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate jps_env

# Install dependencies using pip
echo "Installing dependencies..."
pip install numpy==1.24.3
pip install pandas==2.1.1
pip install flask==2.3.3
pip install sqlalchemy==2.0.21
pip install apscheduler==3.10.4
pip install python-dotenv==1.0.0
pip install selenium==4.15.2
pip install beautifulsoup4==4.12.2
pip install requests==2.31.0
pip install webdriver-manager==4.0.1

# Add the project root to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

echo "Initializing database..."
python src/database/init_db.py

echo "Setup complete!"
echo
echo "To run the application:"
echo "1. Activate the conda environment: conda activate jps_env"
echo "2. Set PYTHONPATH: export PYTHONPATH=\$PYTHONPATH:$(pwd)"
echo "3. Run the application: python app.py"
echo 