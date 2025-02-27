from django.shortcuts import render,get_object_or_404,redirect
from django.http import JsonResponse,StreamingHttpResponse
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
import sys
import subprocess
import platform
from data.function import get_wav_length
from functools import wraps
from decouple import Config,RepositoryEnv
from django.conf import settings
from data.lib.process import is_process_running

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
    ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(ENV_PATH):
        return redirect("/")  
    
    return render(request, "setup.html")

# API zone

@require_http_methods(["DELETE"])
def delete_audio(request, audio_id):
    audio = get_object_or_404(Audio, pk=audio_id)
    if os.path.exists(audio.path):
        try:
            os.remove(audio.path)
        except Exception as e:
            print(f"Error deleting file: {e}")
    audio.delete()

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
    
    try:
        # Retrieve API key from the database
        voice_api_key = Utility.objects.get(name="voice_api_key")
        Apikey = voice_api_key.value
    except Utility.DoesNotExist:
        # Catch if the key does not exist in the database
        return JsonResponse({'error': 'API key not found in the database'}, status=500)
    except Exception as e:
        # General exception for any other database errors
        return JsonResponse({'error': f'Error fetching API key: {str(e)}'}, status=500)
    
    try:
        url = 'https://api.aiforthai.in.th/vaja9/synth_audiovisual'
        headers = {'Apikey':Apikey,'Content-Type' : 'application/json'}
        text = input_text
        data = {'input_text':text,'speaker': 1, 'phrase_break':0, 'audiovisual':0}
        response = requests.post(url, json=data, headers=headers)
        durations=response.json().get('durations')
        if not durations:
            return JsonResponse({'error': 'No durations received in the response'}, status=500)
        rounded_duration = math.ceil(durations)
        rounded_duration=rounded_duration+10
    
    except requests.exceptions.RequestException as e:
        # Catch errors related to the HTTP request (e.g., network issues)
        return JsonResponse({'error': f'Request failed: {str(e)}'}, status=500)
    except ValueError:
        # Catch errors if the response is not in JSON format
        return JsonResponse({'error': 'Invalid response format from the API'}, status=500)
    except Exception as e:
        # General exception for any other errors in this block
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)
    
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
    if os.path.exists(ENV_PATH):
        return JsonResponse({"error": ".env file already exists."}, status=400)

    """Handles the setup process for generating the .env file."""
    if request.method == "POST":
        domain = request.POST.get("domain")

        if not domain:
            return JsonResponse({"error": "All fields are required."}, status=400)
        
        # Regex pattern for validating domain
        domain_pattern = r"^(http:\/\/|https:\/\/)(localhost|\d{1,3}(\.\d{1,3}){3}|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(:\d+)?$"
        if not re.match(domain_pattern, domain):
            return JsonResponse({"error": "Invalid domain format."}, status=400)
        
        """Handles the setup process for generating the .env file."""
        domain = request.POST.get("domain")
        if not domain:
            return JsonResponse({"error": "All fields are required."}, status=400)

        # Generate a random Django SECRET_KEY
        secret_key = secrets.token_urlsafe(50)
        domain_no_port = re.sub(r"^(http:\/\/|https:\/\/)", "", domain) # Remove protocol
        domain_no_port = re.sub(r":\d+$", "", domain_no_port) # Remove port

        # Create and write to .env file
        try:
            with open(ENV_PATH, "w") as env_file:
                env_file.write(f"SECRET_KEY={secret_key}\n")
                env_file.write(f"DEBUG=False\n")
                env_file.write(f"ALLOWED_HOSTS={domain_no_port}\n")
                env_file.write(f"CSRF_TRUSTED_ORIGINS={domain}\n")

            # Execute the script only if not on Windows
            if platform.system() != "Windows":
                subprocess.Popen(["sudo", "systemctl", "restart", "thai_school_alarm_web.service"])

            # Return success response
            return JsonResponse({"message": "Setup completed successfully."}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)



@require_http_methods(["GET"])
def get_current_version(request):
    # Local version.json path
    version_file_path = os.path.join(settings.BASE_DIR, 'version.json')

    try:
        # Read the local version.json
        with open(version_file_path, 'r') as version_file:
            local_data = json.load(version_file)
            current_version = local_data.get('version', 'Unknown')
            supported_python_versions = local_data.get('python_version', [])
    except (FileNotFoundError, json.JSONDecodeError):
        return JsonResponse({"error": "Failed to read local version.json"}, status=500)

    # Get the currently running Python version
    current_python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # URL of the latest version.json on GitHub
    latest_version_url = "https://raw.githubusercontent.com/attane007/thai_school_alarm_web/prod/version.json"

    try:
        # Fetch latest version.json from GitHub
        response = requests.get(latest_version_url, timeout=5)
        response.raise_for_status()
        latest_data = response.json()

        latest_version = latest_data.get('version', 'Unknown')
        release_date = latest_data.get('release_date', 'Unknown')
        changelog = latest_data.get('changelog', [])
        latest_supported_python_versions = latest_data.get('python_version', [])
    except requests.exceptions.RequestException:
        return JsonResponse({
            "version": current_version,
            "latest_version": "Unknown",
            "update_available": False,
            "release_date": "Unknown",
            "changelog": [],
            "current_python_version": current_python_version,
            "compatible_python": "Unknown"
        }, status=500)

    # Check if an update is available
    update_available = current_version != latest_version

    # Fix: Check Python version compatibility properly
    def is_python_version_compatible(version_range):
        """Check if the current Python version falls within a given range."""
        parts = version_range.split(" - ")
        if len(parts) == 2:
            # Range case: "3.10.16 - 3.12"
            min_version, max_version = parts
            return min_version <= current_python_version <= max_version
        elif len(parts) == 1:
            # Single version case: "3.10.16"
            return current_python_version.startswith(parts[0])
        return False

    compatible_python = any(is_python_version_compatible(version) for version in latest_supported_python_versions)

    return JsonResponse({
        "version": current_version,
        "latest_version": latest_version,
        "update_available": update_available,
        "release_date": release_date,
        "changelog": changelog,
        "current_python_version": current_python_version,
        "compatible_python": compatible_python
    })


STATUS_FILE = "process_status.log"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Django root path
SCRIPT_PATH = os.path.join(BASE_DIR, "scripts/update_script.sh")


@require_http_methods(["GET"])
def api_update(request):
    if platform.system() == "Windows":
        return JsonResponse({"error": "Windows is not supported"}, status=400)

    try:
        # ให้สิทธิ์ execute กับ shell script
        subprocess.run(["chmod", "+x", SCRIPT_PATH], check=True)
        
        # รัน shell script
        process = subprocess.Popen(
            [SCRIPT_PATH], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True
        )

        return JsonResponse({
            "message": "Update process started",
            "process_id": process.pid
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@require_http_methods(["GET"])
def api_process(request, process_id):
    if platform.system() == "Windows":
        return JsonResponse({"error": "Windows is not supported"}, status=400)

    # ตรวจสอบว่า process กำลังทำงานอยู่หรือไม่
    if not is_process_running(process_id):
        return JsonResponse({"success": "No process in progress"}, status=200)

    # ถ้า process ทำงานอยู่ ให้ตรวจสอบไฟล์สถานะ
    if not os.path.exists(STATUS_FILE):
        return JsonResponse({"error": "No process in progress"}, status=404)

    try:
        with open(STATUS_FILE, "r") as f:
            status_data = f.read().strip()  # อ่านข้อมูลและลบช่องว่าง/ขึ้นบรรทัดใหม่ส่วนเกิน
        
        if not status_data:
            return JsonResponse({"success": "No process in progress"}, status=200)

        return JsonResponse({"status": "running","log":status_data}, status=200)
    except IOError:
        return JsonResponse({"error": "Failed to read status file"}, status=500)

@csrf_exempt
def upload_file(request):
    UPLOAD_DIR = "audio/uploads/"

    # Ensure the upload directory exists
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]
        
        # Validate file type (only allow MP3)
        if not uploaded_file.name.lower().endswith(".mp3") and not uploaded_file.name.lower().endswith(".wav"):
            return JsonResponse({"error": "อัพโหลดได้เฉพาะไฟล์ MP3 เท่านั้น!"}, status=400)

        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)

        # Save file to disk
        with open(file_path, "wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        # Save file info to the Audio model
        audio = Audio.objects.create(name=uploaded_file.name, path=file_path)

        return JsonResponse({
            "message": f"ไฟล์ {uploaded_file.name} อัพโหลดสำเร็จ!",
            "id": audio.id,
            "name": audio.name,
            "path": audio.path
        })

    return JsonResponse({"error": "อัพโหลดไม่สำเร็จ"}, status=400)