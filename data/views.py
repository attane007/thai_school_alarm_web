from django.shortcuts import render,get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from data.models import Audio, Day, Bell, Schedule
from datetime import datetime
from data.tasks import play_sound,check_schedule
import requests
import os
import shutil
import json
import time

# Create your views here.


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
            except ValueError:
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
    Apikey='GgKWVlLWrUeiFu90YgS01AVwKS0rHTcQ'
    url = 'https://api.aiforthai.in.th/vaja9/synth_audiovisual'
    headers = {'Apikey':Apikey,'Content-Type' : 'application/json'}
    text = input_text
    data = {'input_text':text,'speaker': 1, 'phrase_break':0, 'audiovisual':0}
    response = requests.post(url, json=data, headers=headers)
    print(response.json().get('wav_url'))
    
    time.sleep(3)
    if response.status_code == 200:
        wav_url = response.json().get('wav_url')
        if wav_url:
            resp = requests.get(wav_url, headers={'Apikey': Apikey})
            if resp.status_code == 200:
                temp_dir = 'temp'
                temp_file = os.path.join(temp_dir, 'temp.wav')
                os.makedirs(temp_dir, exist_ok=True)
                try:
                    with open(temp_file, 'wb') as file:
                        file.write(resp.content)
                    play_sound([temp_file])
                    print("File saved to temp/temp.wav")
                finally:
                    shutil.rmtree(temp_dir)
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