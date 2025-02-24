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
    path("", views.index),
    path("save_form",views.save_form),
    path('delete_schedule/<int:schedule_id>/', views.delete_schedule),
    path("speech",views.text_to_speech),
    path("sound",views.sound),
    path("setting",views.setting),
    path("setup",views.setup),
    path("delete_audio/<int:audio_id>/",views.delete_audio),
    path("play_audio/<int:audio_id>/",views.play_audio),
    path("create_audio",views.create_audio),
    path("add_voice_api_key",views.add_voice_api_key),
    path("api/setup/",views.api_setup),
    path('api/version/', views.get_current_version, name='get_current_version'),
    path('api/update/', views.api_update),
    path('api/update/status/', views.api_update),
    path('api/process/<str:process_id>/', views.api_process),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
