#!/bin/bash

echo "=========================================="
echo "JPS Prospect Aggregate Auto-Setup & Launch"
echo "=========================================="

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to print status messages
print_status() {
    echo -e "\n📋 $1"
}

# Function to print success messages
print_success() {
    echo -e "✅ $1"
}

# Function to print error messages
print_error() {
    echo -e "❌ $1"
}

# Check if conda is installed
print_status "Checking for Conda installation..."
if ! command_exists conda; then
    print_error "Conda is not installed. Please install Miniconda or Anaconda first."
    echo "You can download it from: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
else
    print_success "Conda is installed"
fi

# Activate conda environment
print_status "Setting up Conda environment..."
source "$(conda info --base)/etc/profile.d/conda.sh"

# Check if the conda environment exists
if ! conda info --envs | grep -q "jps_env"; then
    echo "Conda environment 'jps_env' not found. Creating..."
    conda create -n jps_env python=3.12 -y
    if [ $? -ne 0 ]; then
        print_error "Failed to create conda environment"
        exit 1
    fi
    print_success "Created conda environment 'jps_env'"
else
    print_success "Found existing conda environment 'jps_env'"
fi

# Activate the environment
conda activate jps_env
if [ $? -ne 0 ]; then
    print_error "Failed to activate conda environment"
    exit 1
fi
print_success "Activated conda environment 'jps_env'"

# Check Python version
print_status "Checking Python version..."
PYTHON_VERSION=$(python --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -ne 3 ] || [ "$PYTHON_MINOR" -lt 10 ]; then
    print_error "Python version $PYTHON_VERSION is not compatible. Updating to Python 3.12..."
    conda install -y python=3.12
    if [ $? -ne 0 ]; then
        print_error "Failed to update Python version"
        exit 1
    fi
else
    print_success "Python version $PYTHON_VERSION is compatible"
fi

# Check if requirements.txt exists
print_status "Checking for requirements.txt..."
if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found. Cannot install dependencies."
    exit 1
else
    print_success "Found requirements.txt"
fi

# Install dependencies
print_status "Installing/updating dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    print_error "Failed to install dependencies"
    exit 1
fi
print_success "Dependencies installed/updated"

# Install Celery dependencies
print_status "Installing Celery dependencies..."
pip install redis celery flower
if [ $? -ne 0 ]; then
    print_error "Failed to install Celery dependencies"
    exit 1
fi
print_success "Celery dependencies installed"

# Check for Redis
print_status "Checking Redis installation..."
if ! command_exists redis-cli; then
    echo "Redis is not installed. Installing Redis..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if ! command_exists brew; then
            print_error "Homebrew is not installed. Please install Homebrew first."
            echo "You can install it from: https://brew.sh/"
            exit 1
        fi
        brew install redis
        if [ $? -ne 0 ]; then
            print_error "Failed to install Redis"
            exit 1
        fi
        print_success "Redis installed"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt-get update && sudo apt-get install -y redis-server
        if [ $? -ne 0 ]; then
            print_error "Failed to install Redis"
            exit 1
        fi
        print_success "Redis installed"
    else
        print_error "Unsupported OS. Please install Redis manually."
        exit 1
    fi
else
    print_success "Redis is installed"
fi

# Check if Redis is running
print_status "Checking if Redis is running..."
if ! redis-cli ping &> /dev/null; then
    echo "Redis is not running. Starting Redis..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew services start redis
        if [ $? -ne 0 ]; then
            print_error "Failed to start Redis"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo systemctl start redis-server
        if [ $? -ne 0 ]; then
            print_error "Failed to start Redis"
            exit 1
        fi
    else
        print_error "Unsupported OS. Please start Redis manually."
        exit 1
    fi
    print_success "Redis started"
else
    print_success "Redis is running"
fi

# Check if start_all.py exists and is executable
print_status "Checking for start_all.py..."
if [ ! -f "start_all.py" ]; then
    print_error "start_all.py not found. Cannot start application."
    exit 1
fi
print_success "Found start_all.py"

# Make the script executable
chmod +x start_all.py
if [ $? -ne 0 ]; then
    print_error "Failed to make start_all.py executable"
    exit 1
fi
print_success "start_all.py is executable"

# Add the project root to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)
print_success "PYTHONPATH updated"

# Initialize database
print_status "Initializing database..."
if [ -f "src/database/init_db.py" ]; then
    python src/database/init_db.py
    if [ $? -ne 0 ]; then
        print_error "Failed to initialize database"
        exit 1
    fi
    print_success "Database initialized"
else
    print_error "Database initialization script not found at src/database/init_db.py"
    print_status "Continuing without database initialization..."
fi

# All checks passed, start the application
print_status "All checks passed! Starting JPS Prospect Aggregate..."
echo "=========================================="
python start_all.py

# If the script exits, deactivate the conda environment
conda deactivate 