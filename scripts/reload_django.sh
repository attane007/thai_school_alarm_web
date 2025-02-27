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

sudo systemctl restart $CELERY_SERVICE_NAME
sudo systemctl restart $CELERY_BEAT_SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

# Return to the original directory
cd "$INITIAL_DIR"
echo "Returned to $INITIAL_DIR"