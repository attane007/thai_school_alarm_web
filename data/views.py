from django.shortcuts import render
from data.models import Audio
import os

# Create your views here.
def index(request):
    audios = Audio.objects.all()

    context = {
        'audios': audios
    }
    return render(request, 'main.html', context)