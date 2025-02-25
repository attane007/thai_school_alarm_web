#!/bin/bash

# Save the initial directory
INITIAL_DIR=$(pwd)

# Variables
PROJECT_DIR="/var/www/thai_school_alarm_web"
VENV_DIR="$PROJECT_DIR/.venv"
SERVICE_NAME="thai_school_alarm_web.service"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
START_PORT=8000
CELERY_SERVICE_NAME="thai_school_alarm_celery.service"
CELERY_BEAT_SERVICE_NAME="thai_school_alarm_beat.service"

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
    for version in 3.10 3.11 3.12; do
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
sudo apt install -y git python3-pip python3-dev libpq-dev python3-venv build-essential libsdl2-mixer-2.0-0 libsdl2-2.0-0 rabbitmq-server

# Enable and start RabbitMQ
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server

# Add RabbitMQ user and permissions
echo "Setting up RabbitMQ user and permissions..."
sudo rabbitmqctl add_user user school_alarm
sudo rabbitmqctl add_vhost /
sudo rabbitmqctl set_permissions -p / user ".*" ".*" ".*"

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
    pip install django daphne celery
fi

# 5. Collect static files for production
echo "Collecting static files..."
python3 manage.py collectstatic --noinput

# 6. Migrate the database
echo "Applying migrations..."
python3 manage.py migrate

# 7. Create the systemd service file for Daphne
echo "Creating Daphne service..."
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Thai School Alarm Service
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

# Create systemd service file for Celery Worker
sudo bash -c "cat > /etc/systemd/system/$CELERY_SERVICE_NAME" <<EOF
[Unit]
Description=Celery Worker for Thai School Alarm
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/celery -A thai_school_alarm_web worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service file for Celery Beat
sudo bash -c "cat > /etc/systemd/system/$CELERY_BEAT_SERVICE_NAME" <<EOF
[Unit]
Description=Celery Beat Scheduler for Thai School Alarm
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/celery -A thai_school_alarm_web beat --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 8. Reload systemd, enable and start the services
echo "Reloading systemd and enabling services..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

# Enable and start Celery Worker and Beat services
sudo systemctl enable $CELERY_SERVICE_NAME
sudo systemctl start $CELERY_SERVICE_NAME
sudo systemctl enable $CELERY_BEAT_SERVICE_NAME
sudo systemctl start $CELERY_BEAT_SERVICE_NAME

# Return to the original directory
cd "$INITIAL_DIR"
echo "Returned to $INITIAL_DIR"
echo "You can access Thai School Alarm from http://your_ip:$AVAILABLE_PORT for Daphne"
