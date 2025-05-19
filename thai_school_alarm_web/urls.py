"""thai_school_alarm_web URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from data import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", views.index, name='index'),
    path("save_form",views.save_form, name='save_form'),
    path('delete_schedule/<int:schedule_id>/', views.delete_schedule, name='delete_schedule'),
    path("speech",views.text_to_speech, name='text_to_speech'),
    path("sound",views.sound, name='sound'),
    path("setting",views.setting, name='setting'),
    path("setup",views.setup, name='setup'),
    path("delete_audio/<int:audio_id>/",views.delete_audio, name='delete_audio'),
    path("play_audio/<int:audio_id>/",views.play_audio, name='play_audio'),
    path("create_audio",views.create_audio, name='create_audio'),
    path("add_voice_api_key",views.add_voice_api_key, name='add_voice_api_key'),
    path("api/setup/",views.api_setup, name='api_setup'),
    path('api/version/', views.get_current_version, name='get_current_version'),
    path('api/update/', views.api_update, name='api_update'),
    path('api/process/<str:process_id>/', views.api_process, name='api_process'),
    path('api/upload/', views.upload_file, name='upload_file'),
    path("stop_audio/", views.stop_audio, name="stop_audio"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
