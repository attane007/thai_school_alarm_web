from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

# Create your models here.
class Audio(models.Model):
    name = models.CharField(max_length=255)
    path = models.TextField()

    def __str__(self):
        return self.name

class Day(models.Model):
    name = models.CharField(max_length=100)
    name_eng = models.CharField(max_length=100,null=True)
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
    enable_bell_sound = models.BooleanField(default=True)  # เพิ่ม field นี้
    def __str__(self):
        return f"Schedule {self.id}"
    
class Utility(models.Model):
    name = models.CharField(max_length=200,unique=True)
    value = models.CharField(max_length=200)

    def __str__(self):
        return self.name

# Signal receiver to remove related Day instances when Schedule is deleted
@receiver(pre_delete, sender=Schedule)
def delete_notification_days(sender, instance, **kwargs):
    instance.notification_days.clear()