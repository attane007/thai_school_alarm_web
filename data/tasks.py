from thai_school_alarm_web.celery import app
from data.models import Schedule
from datetime import datetime
from pytz import timezone
from data.time_sound import tell_hour,tell_minute
from celery.utils.log import get_task_logger
import pygame
import logging

logger = get_task_logger(__name__)

# Set up logging with date and time
logging.basicConfig(
    level=logging.INFO,
    filename='play_sound.log',
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

@app.task
def check_schedule():
    tz = timezone('Asia/Bangkok')  # Define your timezone
    current_time = datetime.now(tz)
    current_day = current_time.strftime('%A')
    hour = current_time.hour
    minute = current_time.minute    
    # Filter schedules based on current hour and minute
    schedules = Schedule.objects.filter(time__hour=hour, time__minute=minute)
    
    for schedule in schedules:
        logger.info(f"Matching schedule found: {schedule}")

        if schedule.notification_days.filter(name_eng=current_day).exists():
            logger.info(f"Today ({current_day}) is a notification day for schedule {schedule}")
            sound_paths=[schedule.bell_sound.first]
            if schedule.tell_time:
                hour_str = f"{hour:02d}"
                minute_str = f"{minute:02d}"
                hour_path = tell_hour(hour_str)
                minute_path = tell_minute(minute_str)
                sound_paths.extend(hour_path)
                sound_paths.extend(minute_path)
            
            sound_paths.append(schedule.sound.path)
            sound_paths.append(schedule.bell_sound.last)
            
            try:
                play_sound(sound_paths=sound_paths)
                logger.info(f"Played sound for schedule: {schedule}")
            except Exception as e:
                logger.info(f"Error playing sound for schedule {schedule}: {e}")
        else:
            logger.info(f"Today ({current_day}) is not a notification day for schedule {schedule}")

        # Implement your logic here
    return f"Checked schedules at {current_time} for hour {hour} and minute {minute}"


@app.task
def play_sound(sound_paths=[]):
    if not sound_paths:
        sound_paths=['audio/bell/sound1/First.wav','audio/bell/sound2/First.wav','audio/bell/sound3/First.wav']
    try:
        pygame.mixer.init()
        for path in sound_paths:
            sound = pygame.mixer.Sound(path)
            sound.play()
            pygame.time.wait(int(sound.get_length() * 1000))  # wait for sound to finish playing
        logging.info("Successfully played all sounds.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        pygame.mixer.quit()

app.conf.beat_schedule = {
    'run_schedule':{
        'task':'data.tasks.play_sound',
        'schedule': 60.0,
    }
}