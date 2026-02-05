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

# WiFi monitoring state
wifi_down_count = 0
last_known_ssid = None

@app.task
def monitor_wifi_connection():
    """
    ตรวจสอบการเชื่อมต่อ WiFi และ fallback เป็น AP หากจำเป็น
    รันทุก 1 นาที
    """
    global wifi_down_count, last_known_ssid
    
    try:
        from data.lib.wifi_manager import (
            check_wifi_connection,
            check_internet_connectivity,
            get_current_wifi,
            is_network_manager_available
        )
        from data.lib.ap_manager import start_ap_mode, stop_ap_mode, is_ap_mode_active
        from data.models import Utility
        
        # ตรวจสอบว่าเปิดใช้งาน monitoring หรือไม่
        try:
            enabled = Utility.objects.filter(name='wifi_monitor_enabled').first()
            if not enabled or enabled.value != 'true':
                logger.info("WiFi monitoring is disabled")
                return "WiFi monitoring disabled"
        except Exception:
            pass  # ถ้ายังไม่มี record ให้ทำงานต่อ
        
        # ตรวจสอบว่ารองรับหรือไม่
        if not is_network_manager_available():
            return "NetworkManager not available"
        
        # ตรวจสอบว่าอยู่ใน AP mode อยู่แล้วหรือไม่
        in_ap_mode = is_ap_mode_active()
        
        if in_ap_mode:
            # อยู่ใน AP mode แล้ว - ตรวจสอบว่า WiFi กลับมาหรือยัง
            logger.info("Currently in AP mode, checking if WiFi is back...")
            
            has_wifi = check_wifi_connection()
            has_internet = check_internet_connectivity()
            
            if has_wifi and has_internet:
                logger.info("WiFi and internet are back! But waiting 5 minutes before switching back...")
                # บันทึกเวลาที่ WiFi กลับมา
                try:
                    wifi_back_time = Utility.objects.filter(name='wifi_back_time').first()
                    if not wifi_back_time:
                        Utility.objects.create(name='wifi_back_time', value=str(datetime.now().timestamp()))
                    else:
                        # ตรวจสอบว่าผ่านไป 5 นาทีหรือยัง
                        back_timestamp = float(wifi_back_time.value)
                        elapsed = datetime.now().timestamp() - back_timestamp
                        
                        if elapsed >= 300:  # 5 นาที
                            logger.info("5 minutes passed, switching back to client mode...")
                            success, message = stop_ap_mode()
                            
                            if success:
                                # Reset state
                                wifi_down_count = 0
                                Utility.objects.filter(name='in_fallback_mode').delete()
                                Utility.objects.filter(name='wifi_back_time').delete()
                                
                                # Record event
                                Utility.objects.filter(name='last_fallback_time').update(
                                    value=str(datetime.now().timestamp())
                                )
                                
                                logger.info("Successfully returned to client mode")
                                return "Returned to client mode"
                            else:
                                logger.error(f"Failed to return to client mode: {message}")
                        else:
                            logger.info(f"Waiting... {300 - elapsed:.0f} seconds remaining")
                except Exception as e:
                    logger.error(f"Error checking WiFi back time: {e}")
            else:
                # ยังไม่มี WiFi/Internet - reset timer
                Utility.objects.filter(name='wifi_back_time').delete()
        
        else:
            # อยู่ใน client mode ปกติ - ตรวจสอบการเชื่อมต่อ
            has_wifi = check_wifi_connection()
            has_internet = check_internet_connectivity()
            
            if has_wifi and has_internet:
                # ทุกอย่างปกติ
                wifi_down_count = 0
                
                # บันทึก SSID ปัจจุบัน
                current = get_current_wifi()
                if current:
                    last_known_ssid = current.get('ssid')
                    Utility.objects.update_or_create(
                        name='last_known_ssid',
                        defaults={'value': last_known_ssid}
                    )
                
                return "WiFi connection OK"
            
            else:
                # WiFi หลุดหรือไม่มี internet
                wifi_down_count += 1
                logger.warning(f"WiFi/Internet down! Count: {wifi_down_count}/3")
                
                if wifi_down_count >= 3:
                    # หลุด 3 รอบติด (3 นาที) - เปิด AP mode
                    logger.warning("WiFi down for 3 minutes, switching to AP mode...")
                    
                    # ดึงค่า config จากฐานข้อมูล
                    try:
                        ap_ssid_obj = Utility.objects.filter(name='ap_ssid').first()
                        ap_password_obj = Utility.objects.filter(name='ap_password').first()
                        
                        ap_ssid = ap_ssid_obj.value if ap_ssid_obj else None
                        ap_password = ap_password_obj.value if ap_password_obj else None
                    except Exception:
                        ap_ssid = None
                        ap_password = None
                    
                    success, message, ap_info = start_ap_mode(
                        ssid=ap_ssid,
                        password=ap_password
                    )
                    
                    if success:
                        # บันทึกสถานะ
                        Utility.objects.update_or_create(
                            name='in_fallback_mode',
                            defaults={'value': 'true'}
                        )
                        Utility.objects.update_or_create(
                            name='last_fallback_time',
                            defaults={'value': str(datetime.now().timestamp())}
                        )
                        
                        # บันทึก AP password ถ้าสุ่มมาใหม่
                        if ap_info.get('password'):
                            Utility.objects.update_or_create(
                                name='ap_password',
                                defaults={'value': ap_info['password']}
                            )
                        
                        # เพิ่มจำนวน fallback
                        try:
                            count_obj = Utility.objects.filter(name='fallback_count').first()
                            if count_obj:
                                count_obj.value = str(int(count_obj.value) + 1)
                                count_obj.save()
                            else:
                                Utility.objects.create(name='fallback_count', value='1')
                        except Exception:
                            pass
                        
                        wifi_down_count = 0
                        logger.info(f"Successfully switched to AP mode: {ap_info}")
                        return f"Switched to AP mode: {message}"
                    else:
                        logger.error(f"Failed to switch to AP mode: {message}")
                        return f"Failed to switch to AP mode: {message}"
    
    except Exception as e:
        logger.error(f"Error in WiFi monitoring: {e}")
        return f"Error: {str(e)}"


app.conf.beat_schedule = {
    'run_schedule':{
        'task':'data.tasks.check_schedule',
        'schedule': crontab(minute='*')
    },
    'monitor-wifi-connection': {
        'task': 'data.tasks.monitor_wifi_connection',
        'schedule': crontab(minute='*/1')  # ทุก 1 นาที
    }
}