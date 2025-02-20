from django.shortcuts import render,get_object_or_404,redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from data.models import Audio, Day, Bell, Schedule, Utility
from datetime import datetime
from data.tasks import play_sound,check_schedule
import requests
import os
import shutil
import json
import time
import math
import secrets
import re
import subprocess
import platform
from data.function import get_wav_length
from functools import wraps
from decouple import Config,RepositoryEnv

def check_env_file(view_func):
    """Decorator to check if the .env file exists and required variables are set."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        print(env_path)

        if not os.path.exists(env_path):
            return redirect('/setup')  # Redirect to setup page if .env is missing

        config = Config(RepositoryEnv(env_path))

        # Define required environment variables
        required_vars = ["DEBUG", "SECRET_KEY","ALLOWED_HOSTS","CSRF_TRUSTED_ORIGINS"]  # Add more required keys if needed
        missing_vars = [var for var in required_vars if not config(var, default=None)]

        if missing_vars:
            print("missing var")
            return redirect('/setup')  # Redirect if required variables are missing

        return view_func(request, *args, **kwargs)

    return _wrapped_view

#template zone
@check_env_file
def index(request):
    audios = Audio.objects.all()
    days = Day.objects.all()
    bells = Bell.objects.all()
    schedules = Schedule.objects.order_by('time')

    context = {
        'audios': audios,
        'days': days,
        'bells': bells,
        'schedules': schedules
    }
    return render(request, 'main.html', context)

def save_form(request):
    if request.method == 'POST':
        try:
            hour = request.POST.get('hour')
            minute = request.POST.get('minute')
            tell_time = request.POST.get('tellTime')
            # Use getlist for multi-select fields
            selected_days = request.POST.getlist('day')
            selected_sound = request.POST.get('sound')
            selected_bell_sound = request.POST.get('bellSound')

            time_str = f"{hour}:{minute}"
            try:
                time_obj = datetime.strptime(time_str, '%H:%M')
            except Exception as e:
                print(f"Exception occurred: {str(e)}")
                return JsonResponse({'error': 'Invalid time format. Must be in HH:MM format.'}, status=400)

            schedule = Schedule(
                # Assuming hour and minute are integers from form
                time=time_obj.time(),
                tell_time=tell_time == '1',  # Convert tellTime string to boolean
                sound=Audio.objects.get(pk=selected_sound),  # Get Audio object
                bell_sound=Bell.objects.get(
                    pk=selected_bell_sound)  # Get Bell object
            )
            schedule.save()

            # Example: Add selected days to Schedule using ManyToMany relationship
            for day_id in selected_days:
                day = Day.objects.get(pk=day_id)
                schedule.notification_days.add(day)

            return JsonResponse({'message': 'Form data saved successfully'}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
def sound(request):
    audios = Audio.objects.all()
    context = {
        'audios': audios,
    }
    return render(request, 'sound.html', context)

def setting(request):
    voice_api_key=Utility.objects.filter(name="voice_api_key").first()
    if voice_api_key:  # Check if the record exists
        # Mask the value if it's longer than 4 characters
        if len(voice_api_key.value) > 4:
            masked_value = 'x' * (len(voice_api_key.value) - 4) + voice_api_key.value[-4:]
        else:
            masked_value = voice_api_key.value
    else:
        # If the record doesn't exist, set masked_value to an empty string or a placeholder
        masked_value = ''
    context = {
        'voice_api_key': masked_value,
    }
    return render(request, 'setting.html', context)

def setup(request):
    return render(request, "setup.html")

# API zone

@require_http_methods(["DELETE"])
def delete_audio(request,audio_id):
    audio = get_object_or_404(Audio, pk=audio_id)
    try:
        os.remove(audio.path)
        audio.delete()
    except Exception:
        print(Exception)
    return JsonResponse({'message': 'Audio deleted successfully.'})

@require_http_methods(["POST"])
def create_audio(request):
    try:
        data = json.loads(request.body)
        input_text = data.get('text')
    except:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    voice_api_key = Utility.objects.get(name="voice_api_key")
    Apikey=voice_api_key.value
    url = 'https://api.aiforthai.in.th/vaja9/synth_audiovisual'
    headers = {'Apikey':Apikey,'Content-Type' : 'application/json'}
    text = input_text
    data = {'input_text':text,'speaker': 1, 'phrase_break':0, 'audiovisual':0}
    response = requests.post(url, json=data, headers=headers)
   
    time.sleep(1)
    if response.status_code == 200:
        wav_url = response.json().get('wav_url')
        if wav_url:
            resp = requests.get(wav_url, headers={'Apikey': Apikey})
            if resp.status_code == 200:
                temp_dir = 'audio/generate'
                temp_name=text+'.wav'
                temp_file = os.path.join(temp_dir, temp_name)
                os.makedirs(temp_dir, exist_ok=True)
                try:
                    with open(temp_file, 'wb') as file:
                        file.write(resp.content)
                    audio=Audio(name=text,path=temp_file)
                    audio.save()
                except Exception:
                    print(Exception)
                return JsonResponse({"status":True,"msg":"Audio created successfully."}, status=200)
            else:
                print(f"Failed to download audio: {resp.reason}")
                return JsonResponse({"status":False,"msg":f"Failed to download audio: {resp.reason}"}, status=200)
        else:
            print("No wav_url found in the response.")
            return JsonResponse({"status":False,"msg":"No wav_url found in the response."}, status=200)
    else:
        print(f"Failed to synthesize speech: {response.reason}")
        return JsonResponse({"status":False,"msg":f"Failed to synthesize speech: {response.reason}"}, status=200)

@require_http_methods(["GET"])
def play_audio(request,audio_id):
    audio = get_object_or_404(Audio, pk=audio_id)
    duration=get_wav_length(audio.path)
    duration=math.ceil(duration)+10
    print(duration)
    abs_dir=os.path.abspath(audio.path)
    try:
        play_sound.delay([abs_dir])
        time.sleep(duration)
    finally:
        pass
    return JsonResponse({'message': 'Audio played successfully.'})

@require_http_methods(["DELETE"])
def delete_schedule(request, schedule_id):
    schedule = get_object_or_404(Schedule, pk=schedule_id)
    schedule.delete()
    return JsonResponse({'message': 'Schedule deleted successfully.'})

@require_http_methods(["POST"])
def text_to_speech(request):
    try:
        data = json.loads(request.body)
        input_text = data.get('text')
    except:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    voice_api_key=Utility.objects.get(name="voice_api_key")
    Apikey=voice_api_key.value
    url = 'https://api.aiforthai.in.th/vaja9/synth_audiovisual'
    headers = {'Apikey':Apikey,'Content-Type' : 'application/json'}
    text = input_text
    data = {'input_text':text,'speaker': 1, 'phrase_break':0, 'audiovisual':0}
    response = requests.post(url, json=data, headers=headers)
    durations=response.json().get('durations')
    rounded_duration = math.ceil(durations)
    rounded_duration=rounded_duration+10
    
    time.sleep(1)
    if response.status_code == 200:
        wav_url = response.json().get('wav_url')
        if wav_url:
            resp = requests.get(wav_url, headers={'Apikey': Apikey})
            if resp.status_code == 200:
                temp_dir = os.path.abspath('temp')
                temp_file = os.path.join(temp_dir, 'temp.wav')
                os.makedirs(temp_dir, exist_ok=True)
                try:
                    with open(temp_file, 'wb') as file:
                        file.write(resp.content)
                    play_sound.delay([temp_file])
                    time.sleep(rounded_duration)
                finally:
                    shutil.rmtree(temp_dir)
                    pass
                return JsonResponse({"status":True,"msg":"success"}, status=200)
            else:
                print(f"Failed to download audio: {resp.reason}")
                return JsonResponse({"status":False,"msg":f"Failed to download audio: {resp.reason}"}, status=200)
        else:
            print("No wav_url found in the response.")
            return JsonResponse({"status":False,"msg":"No wav_url found in the response."}, status=200)
    else:
        print(f"Failed to synthesize speech: {response.reason}")
        return JsonResponse({"status":False,"msg":f"Failed to synthesize speech: {response.reason}"}, status=200)

@require_http_methods(["POST"])
def add_voice_api_key(request):
    try:
        data = json.loads(request.body)  
        voice_api_key = data.get('voice_api_key', '')


        if voice_api_key:
            existing_key = Utility.objects.filter(name='voice_api_key').first()
            
            if existing_key:
                existing_key.value = voice_api_key
                existing_key.save()
                return JsonResponse({'message': 'API Key updated successfully'}, status=200)
            else:
                Utility.objects.create(name='voice_api_key', value=voice_api_key)
                return JsonResponse({'message': 'API Key created successfully'}, status=201)
        else:
            return JsonResponse({'error': 'No API key provided'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def api_setup(request):
    ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    SCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reload_django.sh')  # Path to the .sh script

    """Handles the setup process for generating the .env file."""
    if request.method == "POST":
        domain = request.POST.get("domain")

        if not domain:
            return JsonResponse({"error": "All fields are required."}, status=400)
        
        # Regex pattern for validating domain
        domain_pattern = r"^(https?:\/\/)?(localhost|\d{1,3}(\.\d{1,3}){3}|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(:\d+)?$"
        if not re.match(domain_pattern, domain):
            return JsonResponse({"error": "Invalid domain format."}, status=400)
        
        """Handles the setup process for generating the .env file."""
        domain = request.POST.get("domain")
        if not domain:
            return JsonResponse({"error": "All fields are required."}, status=400)

        # Generate a random Django SECRET_KEY
        secret_key = secrets.token_urlsafe(50)

        # Create and write to .env file
        try:
            with open(ENV_PATH, "w") as env_file:
                env_file.write(f"SECRET_KEY={secret_key}\n")
                env_file.write(f"DEBUG=False\n")
                env_file.write(f"ALLOWED_HOSTS={domain}\n")
                env_file.write(f"CSRF_TRUSTED_ORIGINS={domain}\n")

            # Execute the script only if not on Windows
            print(SCRIPT_PATH)
            if platform.system() != "Windows":
                if not os.path.exists(SCRIPT_PATH):
                    return JsonResponse({"error": f"Script not found at {SCRIPT_PATH}"}, status=500)
                subprocess.run(["chmod", "+x", SCRIPT_PATH], check=True)
                result = subprocess.run(["/bin/bash", SCRIPT_PATH], capture_output=True, text=True)

            # Return success response
            return JsonResponse({"message": "Setup completed successfully."}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)