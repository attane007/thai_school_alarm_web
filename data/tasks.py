from thai_school_alarm_web.celery import app
from data.models import Schedule
from datetime import datetime
from pytz import timezone
from data.time_sound import tell_hour,tell_minute
from celery.utils.log import get_task_logger
import logging
import subprocess
from celery.schedules import crontab
import os
import signal
import threading

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
    tz = timezone('Asia/Bangkok')
    current_time = datetime.now(tz)
    current_day = current_time.strftime('%A')
    hour = current_time.hour
    minute = current_time.minute
    schedules = Schedule.objects.filter(time__hour=hour, time__minute=minute)

    for schedule in schedules:
        logger.info(f"Matching schedule found: {schedule}")

        if schedule.notification_days.filter(name_eng=current_day).exists():
            logger.info(f"Today ({current_day}) is a notification day for schedule {schedule}")
            sound_paths = []
            # เงื่อนไขใหม่: ถ้า enable_bell_sound ให้เพิ่มเสียงระฆัง
            if schedule.enable_bell_sound and schedule.bell_sound:
                sound_paths.append(schedule.bell_sound.first)
            if schedule.tell_time:
                hour_str = f"{hour:02d}"
                minute_str = f"{minute:02d}"
                hour_path = tell_hour(hour_str)
                minute_path = tell_minute(minute_str)
                sound_paths.extend(hour_path)
                sound_paths.extend(minute_path)
            if schedule.sound:
                sound_paths.append(schedule.sound.path)
            # เพิ่มเสียงระฆังท้ายถ้า enable_bell_sound
            if schedule.enable_bell_sound and schedule.bell_sound:
                sound_paths.append(schedule.bell_sound.last)
            try:
                play_sound(sound_paths=sound_paths)
                logger.info(f"Played sound for schedule: {schedule}")
            except Exception as e:
                logger.info(f"Error playing sound for schedule {schedule}: {e}")
        else:
            logger.info(f"Today ({current_day}) is not a notification day for schedule {schedule}")
    return f"Checked schedules at {current_time} for hour {hour} and minute {minute}"


current_process = None
play_thread = None
stop_event = threading.Event()

@app.task
def play_sound(sound_paths=[]):
    global current_process, play_thread, stop_event

    # ถ้ามีแค่ 1 เพลง ให้ต่อเสียงระฆังหัว-ท้าย
    if not sound_paths:
        sound_paths = ['audio/bell/sound1/First.wav', 'audio/bell/sound2/First.wav', 'audio/bell/sound3/First.wav']
    elif len(sound_paths) == 1:
        sound_paths = ['audio/bell/sound1/First.wav', sound_paths[0], 'audio/bell/sound1/First.wav']

    def play_sequence():
        global current_process, stop_event
        for path in sound_paths:
            if stop_event.is_set():
                break
            command = ['ffplay', '-nodisp', '-autoexit', path]
            try:
                if os.name == 'nt':
                    current_process = subprocess.Popen(
                        command,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    current_process = subprocess.Popen(
                        command,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                current_process.wait()
            except Exception as e:
                logging.error(f"Error playing {path}: {e}")
            finally:
                current_process = None
        stop_event.clear()
        logging.info("Finished playing all sounds.")

    stop_sound()  # หยุดเสียงที่กำลังเล่นก่อน (ถ้ามี)
    stop_event.clear()
    play_thread = threading.Thread(target=play_sequence, daemon=True)
    play_thread.start()
    logging.info("Started play_sound thread.")

def stop_sound():
    global current_process, play_thread, stop_event
    stop_event.set()
    if current_process and current_process.poll() is None:
        try:
            if os.name == 'nt':
                current_process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                current_process.terminate()
        except Exception:
            try:
                current_process.kill()
            except Exception:
                pass
    current_process = None
    logging.info("Stopped current playing sound.")

app.conf.beat_schedule = {
    'run_schedule':{
        'task':'data.tasks.check_schedule',
        'schedule': crontab(minute='*')
    }
}