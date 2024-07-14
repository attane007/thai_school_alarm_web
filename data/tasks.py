from thai_school_alarm_web.celery import app
from celery.utils.log import get_task_logger
import pygame

logger = get_task_logger(__name__)


@app.task
def play_sound():
    sound_paths=['audio/bell/sound1/First.wav','audio/bell/sound2/First.wav','audio/bell/sound3/First.wav']
    try:
        pygame.mixer.init()
        for path in sound_paths:
            sound = pygame.mixer.Sound(path)
            sound.play()
            pygame.time.wait(int(sound.get_length() * 1000))  # wait for sound to finish playing
    except Exception as e:
        pass
    finally:
        pygame.mixer.quit()

app.conf.beat_schedule = {
    'run_schedule':{
        'task':'data.tasks.play_sound',
        'schedule': 60.0,
    }
}