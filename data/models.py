from django.db import models

# Create your models here.
class Day(models.Model):
    name = models.CharField(max_length=100)  # Store the name of the day
    def __str__(self):
        return self.name
    
class Schedule(models.Model):
    notification_days = models.ManyToManyField(Day, blank=True)  # วันแจ้งเตือน
    time = models.TimeField(null=True, blank=True)  # เวลาแจ้งเตือน
    sound = models.TextField(null=True, blank=True)  # เสียงแจ้งเตือน
    bell_sound = models.TextField(null=True, blank=True)  # เสียงระฆัง
    status = models.BooleanField(default=False)  # Status field
    tell_time = models.BooleanField(default=False)  # การบอกเวลา
    sound_eng = models.TextField(null=True, blank=True)  # เสียงแจ้งเตือนภาษาอังกฤษ
    def __str__(self):
        return f"Schedule {self.id}"
    
class Bell(models.Model):
    name = models.CharField(max_length=200)
    first = models.TextField()
    last = models.TextField()
    status = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
class Utility(models.Model):
    name = models.CharField(max_length=200)
    value = models.CharField(max_length=200)

    def __str__(self):
        return self.name