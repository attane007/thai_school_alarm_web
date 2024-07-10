from django.db import models

# Create your models here.
class Schedule(models.Model):
    time = models.TimeField(null=True, blank=True)
    sound = models.TextField(null=True, blank=True)
    sound_eng = models.TextField(null=True, blank=True)
    status = models.BooleanField(default=False)
    tell_time = models.BooleanField(default=False)

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