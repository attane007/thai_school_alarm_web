from django.shortcuts import render
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
import pygame
import os

def check_initial(view_func):
    def wrapper(request, *args, **kwargs):
        # Check if db.sqlite3 file exists
        db_file = 'db.sqlite3'  # Replace with your actual path
        if not os.path.exists(db_file):
            # Run makemigrations and migrate
            try:
                call_command('makemigrations', 'data')
                call_command('migrate')
            except CommandError as e:
                # Handle any errors that may occur during migrations
                return render(request, 'error.html', {'error_message': str(e)})
        cursor = connection.cursor()
        table_name = 'data_bell'  # Replace with your actual table name
        table_exists = False
        try:
            cursor.execute(f"SELECT 1 FROM {table_name} LIMIT 1;")
            table_exists = True
        except Exception as ex:
            # Handle exception if needed
            pass
        finally:
            cursor.close()

        if not table_exists:
            # Run makemigrations and migrate again if the table doesn't exist
            cursor = connection.cursor()
            try:
                call_command('makemigrations', 'data')
                call_command('migrate')                
                cursor.execute('''
                    INSERT INTO data_bell (name,first,last,status)
                    VALUES ('เสียงเตือนที่ 1', 'audio/bell/sound1/First.wav','audio/bell/sound1/Last.wav',0),
                           ('เสียงเตือนที่ 2', 'audio/bell/sound2/First.wav','audio/bell/sound2/Last.wav',0),
                           ('เสียงเตือนที่ 3', 'audio/bell/sound3/First.wav','audio/bell/sound3/Last.wav',1)
                ''')
            except CommandError as e:
                # Handle any errors that may occur during migrations
                return render(request, 'error.html', {'error_message': str(e)})
            finally:
                cursor.close()
        
        # Call the original view function
        return view_func(request, *args, **kwargs)
    
    return wrapper


# Create your views here.
@check_initial
def index(request):
    # Add any necessary logic here
    pygame.mixer.init()
    # sound_paths=['audio/bell/sound1/First.wav','audio/bell/sound2/First.wav','audio/bell/sound3/First.wav']
    # try:
    #     for path in sound_paths:
    #         sound = pygame.mixer.Sound(path)
    #         sound.play()
    #         pygame.time.wait(int(sound.get_length() * 1000))  # wait for sound to finish playing
    # finally:
    #     pygame.mixer.quit()

    context = {
        'message': 'Hello, World!'  # Example context data
    }
    return render(request, 'base.html', context)