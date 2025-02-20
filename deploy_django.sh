#!/bin/bash

# Save the initial directory
INITIAL_DIR=$(pwd)

# Variables
PROJECT_DIR="/var/www/thai_school_alarm_web"
VENV_DIR="$PROJECT_DIR/.venv"
SERVICE_NAME="django_daphne.service"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
START_PORT=8000

# Function to find an available port
find_available_port() {
    local port=$START_PORT
    while ss -tuln | grep -q ":$port "; do
        ((port++))
    done
    echo $port
}

# Find a free port
AVAILABLE_PORT=$(find_available_port)
echo "Using port $AVAILABLE_PORT for Daphne"

# Function to check if a required Python version is installed
check_python_version() {
    for version in 3.10 3.11; do
        if command -v python$version &>/dev/null; then
            echo "Using Python $version"
            PYTHON_VERSION="python$version"
            return
        fi
    done
    echo "Python 3.10 or 3.11 not found. Please install one of these versions."
    exit 1
}

# Check and set Python version
check_python_version

# 1. Install required packages
echo "Installing required packages..."
sudo apt update
sudo apt install -y git python3-pip python3-dev libpq-dev python3-venv build-essential

# Ensure /var/www exists and set correct ownership
if [ ! -d "/var/www" ]; then
    echo "Creating /var/www directory..."
    sudo mkdir -p /var/www
    sudo chown $USER:$USER /var/www
fi

cd /var/www

# 2. Clone or update the repository
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Cloning repository into /var/www..."
    git clone -b prod https://github.com/attane007/thai_school_alarm_web.git
else
    echo "Repository already exists. Pulling latest changes..."
    cd $PROJECT_DIR
    git pull origin prod || { echo "Failed to pull latest changes"; exit 1; }
fi

cd $PROJECT_DIR

# 3. Create and activate virtual environment
echo "Setting up virtual environment..."
$PYTHON_VERSION -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# 4. Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "requirements.txt not found. Installing Django and Daphne only..."
    pip install django daphne
fi

# 5. Collect static files for production
echo "Collecting static files..."
python3 manage.py collectstatic --noinput

# 6. Migrate the database
echo "Applying migrations..."
python3 manage.py migrate

# 7. Create a systemd service for Daphne
echo "Creating systemd service..."

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Django Daphne Service
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/daphne -b 0.0.0.0 -p $AVAILABLE_PORT thai_school_alarm_web.asgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 6. Reload systemd, enable and start the service
echo "Reloading systemd and enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

# Return to the original directory
cd "$INITIAL_DIR"
echo "Returned to $INITIAL_DIR"