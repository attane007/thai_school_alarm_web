from django.test import TestCase
from data.models import Audio, Day, Bell, Schedule, Utility
# Create your tests here.

class ModelTests(TestCase):

    def setUp(self):
        # Set up any data that is used across multiple tests
        self.audio = Audio.objects.create(name="Test Audio", path="/media/audio.mp3")
        self.day = Day.objects.create(name="วันจันทร์", name_eng="Monday")
        self.bell = Bell.objects.create(name="Test Bell", first="First Bell Sound", last="Last Bell Sound", status=True)
        self.utility = Utility.objects.create(name="Timezone", value="Asia/Bangkok")

    def test_audio_model(self):
        """Test that Audio model is created correctly"""
        audio = Audio.objects.get(id=self.audio.id)
        self.assertEqual(audio.name, "Test Audio")
        self.assertEqual(audio.path, "/media/audio.mp3")
        self.assertEqual(str(audio), "Test Audio")

    def test_day_model(self):
        """Test that Day model is created correctly"""
        day = Day.objects.get(id=self.day.id)
        self.assertEqual(day.name, "วันจันทร์")
        self.assertEqual(day.name_eng, "Monday")
        self.assertEqual(str(day), "วันจันทร์")

    def test_bell_model(self):
        """Test that Bell model is created correctly"""
        bell = Bell.objects.get(id=self.bell.id)
        self.assertEqual(bell.name, "Test Bell")
        self.assertEqual(bell.first, "First Bell Sound")
        self.assertEqual(bell.last, "Last Bell Sound")
        self.assertEqual(bell.status, True)
        self.assertEqual(str(bell), "Test Bell")

    def test_utility_model(self):
        """Test that Utility model is created correctly"""
        utility = Utility.objects.get(id=self.utility.id)
        self.assertEqual(utility.name, "Timezone")
        self.assertEqual(utility.value, "Asia/Bangkok")
        self.assertEqual(str(utility), "Timezone")

    def test_schedule_model(self):
        """Test that Schedule model is created correctly and handles relations"""
        # Create a schedule related to existing Audio and Bell models
        schedule = Schedule.objects.create(
            time="12:00:00",
            sound=self.audio,
            bell_sound=self.bell,
            tell_time=False
        )
        schedule.notification_days.add(self.day)  # Add a day to notification days

        # Fetch the schedule from the database
        schedule_from_db = Schedule.objects.get(id=schedule.id)

        # Verify relations and fields
        self.assertEqual(schedule_from_db.sound, self.audio)
        self.assertEqual(schedule_from_db.bell_sound, self.bell)
        self.assertFalse(schedule_from_db.tell_time)
        self.assertIn(self.day, schedule_from_db.notification_days.all())
        self.assertEqual(str(schedule_from_db), f"Schedule {schedule.id}")