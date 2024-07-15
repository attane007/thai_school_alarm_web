from django.db import models

# Create your models here.
class Audio(models.Model):
    name = models.CharField(max_length=255)
    path = models.TextField()

    def __str__(self):
        return self.name

class Day(models.Model):
    name = models.CharField(max_length=100)  # Store the name of the day
    def __str__(self):
        return self.name
    
class Bell(models.Model):
    name = models.CharField(max_length=200)
    first = models.TextField()
    last = models.TextField()
    status = models.BooleanField(default=False)

    def __str__(self):
        return self.name
        
class Schedule(models.Model):
    notification_days = models.ManyToManyField(Day, blank=True)  # วันแจ้งเตือน
    time = models.TimeField(null=True, blank=True)  # เวลาแจ้งเตือน
    sound = models.ForeignKey(Audio, on_delete=models.SET_NULL, null=True, blank=True)
    bell_sound = models.ForeignKey(Bell, on_delete=models.SET_NULL, null=True, blank=True)  # เสียงระฆัง
    tell_time = models.BooleanField(default=True)
    def __str__(self):
        return f"Schedule {self.id}"
    
class Utility(models.Model):
    name = models.CharField(max_length=200)
    value = models.CharField(max_length=200)

    def __str__(self):
        return self.name