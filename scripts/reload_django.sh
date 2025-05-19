#!/bin/bash

# Save the initial directory
INITIAL_DIR=$(pwd)

# Variables
PROJECT_DIR="/var/www/thai_school_alarm_web"
VENV_DIR="$PROJECT_DIR/.venv"
SERVICE_NAME="thai_school_alarm_web.service"
CELERY_SERVICE_NAME="thai_school_alarm_celery.service"
CELERY_BEAT_SERVICE_NAME="thai_school_alarm_beat.service"

cd $PROJECT_DIR
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

echo "Backing up systemd service files before update..."
sudo cp /etc/systemd/system/$CELERY_SERVICE_NAME /etc/systemd/system/${CELERY_SERVICE_NAME}.bak 2>/dev/null || true
sudo cp /etc/systemd/system/$CELERY_BEAT_SERVICE_NAME /etc/systemd/system/${CELERY_BEAT_SERVICE_NAME}.bak 2>/dev/null || true

# Create/update systemd service file for Celery Worker (from template)
export USER
export PROJECT_DIR
export VENV_DIR
envsubst < $PROJECT_DIR/scripts/celery_worker.service.template | sudo tee /etc/systemd/system/$CELERY_SERVICE_NAME > /dev/null

# Create/update systemd service file for Celery Beat (from template)
envsubst < $PROJECT_DIR/scripts/celery_beat.service.template | sudo tee /etc/systemd/system/$CELERY_BEAT_SERVICE_NAME > /dev/null

sudo systemctl daemon-reload

# Recovery logic if restart fails
if ! sudo systemctl restart $CELERY_SERVICE_NAME; then
    echo "[ERROR] Celery Worker restart failed! Restoring previous service file..."
    sudo cp /etc/systemd/system/${CELERY_SERVICE_NAME}.bak /etc/systemd/system/$CELERY_SERVICE_NAME
    sudo systemctl daemon-reload
    sudo systemctl restart $CELERY_SERVICE_NAME
fi

if ! sudo systemctl restart $CELERY_BEAT_SERVICE_NAME; then
    echo "[ERROR] Celery Beat restart failed! Restoring previous service file..."
    sudo cp /etc/systemd/system/${CELERY_BEAT_SERVICE_NAME}.bak /etc/systemd/system/$CELERY_BEAT_SERVICE_NAME
    sudo systemctl daemon-reload
    sudo systemctl restart $CELERY_BEAT_SERVICE_NAME
fi

if ! sudo systemctl restart $SERVICE_NAME; then
    echo "[ERROR] Daphne restart failed! Please check the service manually."
fi

# Return to the original directory
cd "$INITIAL_DIR"
echo "Returned to $INITIAL_DIR"