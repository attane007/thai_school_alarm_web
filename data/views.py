from django.shortcuts import render,get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from data.models import Audio, Day, Bell, Schedule
from datetime import datetime
from data.tasks import play_sound,check_schedule
import requests
import os
import shutil
import json
import time
import math
import wave

# Create your views here.
def get_wav_length(file_path):
    with wave.open(file_path, 'rb') as wav_file:
        # Get the number of frames and the frame rate
        num_frames = wav_file.getnframes()
        frame_rate = wav_file.getframerate()
        # Calculate the duration in seconds
        duration = num_frames / float(frame_rate)
        return duration

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
    Apikey=settings.voice_api_key
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
    
def setting(request):
    audios = Audio.objects.all()
    context = {
        'audios': audios,
    }
    return render(request, 'setting.html', context)

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
    Apikey=settings.voice_api_key
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