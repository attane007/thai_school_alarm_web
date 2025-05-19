from django.test import TestCase, Client
from data.models import Audio, Day, Bell, Schedule, Utility
from django.urls import reverse
from unittest.mock import patch, MagicMock, mock_open, call
import json
import os
from django.conf import settings as django_settings # Renamed to avoid conflict
from datetime import time as dt_time
import data.views # Required for path calculations
import requests # For requests.exceptions.RequestException
import subprocess # For subprocess.CalledProcessError, subprocess.PIPE
from django.core.files.uploadedfile import SimpleUploadedFile # Added import
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

class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.mock_base_dir = '/fake/basedir'

        # Patch settings.BASE_DIR as used in data.views
        self.patch_settings_base_dir = patch('data.views.settings.BASE_DIR', self.mock_base_dir)
        self.patch_settings_base_dir.start()

        self.audio1 = Audio.objects.create(name="Test Audio 1", path="fixtures/audio1.mp3") # Changed to relative path
        self.day1 = Day.objects.create(name="วันจันทร์", name_eng="Monday")
        self.bell1 = Bell.objects.create(name="Test Bell 1", first="First1.wav", last="Last1.wav", status=True)
        # Ensure no other key exists that might interfere
        Utility.objects.filter(name="voice_api_key").delete()
        self.utility_api_key = Utility.objects.create(name="voice_api_key", value="testapikey") # 10 chars
        self.schedule1 = Schedule.objects.create(
            time=dt_time(10, 0, 0),
            sound=self.audio1,
            bell_sound=self.bell1,
            tell_time=True
        )
        self.schedule1.notification_days.add(self.day1)

        # Path for .env file as calculated in views.py's decorator and setup view
        self.views_file_path = os.path.abspath(data.views.__file__)
        self.project_root_path = os.path.dirname(os.path.dirname(self.views_file_path))
        self.env_file_path_in_views = os.path.join(self.project_root_path, '.env')

        self.mock_play_sound_task = patch('data.views.play_sound').start()
        self.mock_requests_post = patch('data.views.requests.post').start()
        self.mock_requests_get = patch('data.views.requests.get').start()
        self.mock_os_path_exists = patch('data.views.os.path.exists').start()
        self.mock_os_remove = patch('data.views.os.remove').start()
        self.mock_os_makedirs = patch('data.views.os.makedirs').start()
        self.mock_shutil_rmtree = patch('data.views.shutil.rmtree').start()
        self.mock_builtin_open = patch('builtins.open', new_callable=mock_open).start() # For general file ops
        self.mock_views_open = patch('data.views.open', new_callable=mock_open).start() # Specifically for open in views if not builtin
        self.mock_config_class = patch('data.views.Config').start()
        self.mock_repository_env_class = patch('data.views.RepositoryEnv').start()
        self.mock_platform_system = patch('data.views.platform.system').start()
        self.mock_subprocess_popen = patch('data.views.subprocess.Popen').start()
        self.mock_subprocess_run = patch('data.views.subprocess.run').start()
        self.mock_is_process_running = patch('data.views.is_process_running').start()
        
        self.mock_platform_system.return_value = "Linux"
        self.mock_os_path_exists.return_value = False # Default: .env does not exist, other paths might not exist
        
        self.mock_config_instance = MagicMock()
        self.mock_config_class.return_value = self.mock_config_instance
        self.mock_config_instance.side_effect = lambda key, default=None: {
            "DEBUG": "True", "SECRET_KEY": "akey", "ALLOWED_HOSTS": "localhost", "CSRF_TRUSTED_ORIGINS": "http://localhost"
        }.get(key, default)

    def tearDown(self):
        patch.stopall()

    # Tests for check_env_file decorator (via index view)
    def test_check_env_file_decorator_no_env_file(self):
        self.mock_os_path_exists.side_effect = lambda path: path != self.env_file_path_in_views
        response = self.client.get(reverse('index'))
        self.assertRedirects(response, '/setup')
        self.mock_os_path_exists.assert_any_call(self.env_file_path_in_views)

    def test_check_env_file_decorator_missing_vars(self):
        self.mock_os_path_exists.side_effect = lambda path: path == self.env_file_path_in_views
        self.mock_config_instance.side_effect = lambda key, default=None: {"DEBUG": "True"}.get(key, default) # Missing SECRET_KEY
        response = self.client.get(reverse('index')) # This call is decorated
        self.assertRedirects(response, '/setup', fetch_redirect_response=False) # Tell it not to follow

    # index view
    def test_index_view_success(self):
        self.mock_os_path_exists.side_effect = lambda path: path == self.env_file_path_in_views # .env exists
        # Default mock_config_instance is fine for success
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main.html')
        self.assertIn('audios', response.context)
        self.assertEqual(list(response.context['schedules']), [self.schedule1])

    # save_form view
    def test_save_form_success(self):
        data = {
            'hour': '10', 'minute': '30', 'tellTime': '1',
            'enable_bell_sound': '1',
            'day': [str(self.day1.id)], 'sound': str(self.audio1.id),
            'bellSound': str(self.bell1.id)
        }
        response = self.client.post(reverse('save_form'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['message'], 'Form data saved successfully')
        schedule = Schedule.objects.filter(time=dt_time(10, 30, 0)).first()
        self.assertIsNotNone(schedule)
        self.assertTrue(schedule.enable_bell_sound)
        self.assertIsNotNone(schedule.bell_sound)

    def test_save_form_disable_bell_sound(self):
        data = {
            'hour': '11', 'minute': '15', 'tellTime': '0',
            'enable_bell_sound': '0',
            'day': [str(self.day1.id)], 'sound': str(self.audio1.id),
            'bellSound': str(self.bell1.id)  # Should be ignored
        }
        response = self.client.post(reverse('save_form'), data)
        self.assertEqual(response.status_code, 200)
        schedule = Schedule.objects.filter(time=dt_time(11, 15, 0)).first()
        self.assertIsNotNone(schedule)
        self.assertFalse(schedule.enable_bell_sound)
        self.assertIsNone(schedule.bell_sound)

    def test_save_form_invalid_time_format(self):
        data = {'hour': 'invalid', 'minute': '30', 'tellTime': '1', 'day': [str(self.day1.id)], 'sound': str(self.audio1.id), 'bellSound': str(self.bell1.id)}
        response = self.client.post(reverse('save_form'), data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid time format', response.json()['error'])

    def test_save_form_invalid_method(self):
        response = self.client.get(reverse('save_form'))
        self.assertEqual(response.status_code, 405)

    # sound view
    def test_sound_view(self):
        response = self.client.get(reverse('sound'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sound.html')
        self.assertIn('audios', response.context)

    # setting view
    def test_setting_view_with_api_key(self):
        response = self.client.get(reverse('setting'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'setting.html')
        # Fix: Masked value should be 6 x + last 4 chars of 'testapikey' = 'xxxxxxikey'
        self.assertEqual(response.context['voice_api_key'], 'xxxxxxikey')

    def test_setting_view_no_api_key(self):
        Utility.objects.get(name="voice_api_key").delete()
        response = self.client.get(reverse('setting'))
        self.assertEqual(response.context['voice_api_key'], '')

    # setup view
    def test_setup_view_env_exists(self):
        self.mock_os_path_exists.side_effect = lambda path: path == self.env_file_path_in_views
        response = self.client.get(reverse('setup'))
        self.assertRedirects(response, '/')

    def test_setup_view_no_env(self):
        self.mock_os_path_exists.side_effect = lambda path: path != self.env_file_path_in_views
        response = self.client.get(reverse('setup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'setup.html')

    # delete_audio view
    def test_delete_audio_success(self):
        self.mock_os_path_exists.return_value = True # File exists at audio1.path
        response = self.client.delete(reverse('delete_audio', args=[self.audio1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Audio.objects.filter(id=self.audio1.id).exists())
        self.mock_os_remove.assert_called_with(self.audio1.path)

    def test_delete_audio_not_found(self):
        response = self.client.delete(reverse('delete_audio', args=[999]))
        self.assertEqual(response.status_code, 404)

    # create_audio view
    def test_create_audio_success(self):
        self.mock_requests_post.return_value.status_code = 200
        self.mock_requests_post.return_value.json.return_value = {'wav_url': 'http://example.com/audio.wav'}
        self.mock_requests_get.return_value.status_code = 200 # For downloading the wav
        self.mock_requests_get.return_value.content = b'audio content'
        
        response = self.client.post(reverse('create_audio'), json.dumps({'text': 'สวัสดี'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['status'])
        self.assertTrue(Audio.objects.filter(name='สวัสดี').exists())
        self.mock_os_makedirs.assert_called_with('audio/generate', exist_ok=True)
        self.mock_views_open.assert_called_with(os.path.join('audio/generate', 'สวัสดี.wav'), 'wb')

    def test_create_audio_synth_fail(self):
        self.mock_requests_post.return_value.status_code = 500
        self.mock_requests_post.return_value.reason = "Server Error"
        response = self.client.post(reverse('create_audio'), json.dumps({'text': 'test'}), content_type='application/json')
        self.assertEqual(response.status_code, 200) # View returns 200 with status:False
        self.assertFalse(response.json()['status'])
        self.assertIn("Failed to synthesize speech", response.json()['msg'])

    # play_audio view
    def test_play_audio_success(self):
        response = self.client.get(reverse('play_audio', args=[self.audio1.id]))
        self.assertEqual(response.status_code, 200)
        self.mock_play_sound_task.assert_called_once_with([os.path.abspath(self.audio1.path)])

    # delete_schedule view
    def test_delete_schedule_success(self):
        response = self.client.delete(reverse('delete_schedule', args=[self.schedule1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Schedule.objects.filter(id=self.schedule1.id).exists())

    # text_to_speech view
    @patch('data.views.time.sleep')
    def test_text_to_speech_success(self, mock_sleep):
        self.mock_requests_post.return_value.status_code = 200
        self.mock_requests_post.return_value.json.return_value = {'wav_url': 'http://example.com/temp.wav', 'durations': 2.5}
        self.mock_requests_get.return_value.status_code = 200
        self.mock_requests_get.return_value.content = b'temp audio'
        
        response = self.client.post(reverse('text_to_speech'), json.dumps({'text': 'ทดสอบ'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['status'])
        temp_dir = os.path.abspath('temp')
        self.mock_os_makedirs.assert_called_with(temp_dir, exist_ok=True)
        self.mock_views_open.assert_called_with(os.path.join(temp_dir, 'temp.wav'), 'wb')
        self.mock_play_sound_task.assert_called_with([os.path.join(temp_dir, 'temp.wav')])
        mock_sleep.assert_called_with(3) # ceil(2.5)
        self.mock_shutil_rmtree.assert_called_with(temp_dir)

    def test_text_to_speech_api_key_not_found(self):
        Utility.objects.get(name="voice_api_key").delete()
        response = self.client.post(reverse('text_to_speech'), json.dumps({'text': 'test'}), content_type='application/json')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()['error'], 'API key not found in the database')

    # add_voice_api_key view
    def test_add_voice_api_key_create(self):
        Utility.objects.filter(name='voice_api_key').delete()
        response = self.client.post(reverse('add_voice_api_key'), json.dumps({'voice_api_key': 'newkey'}), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Utility.objects.filter(name='voice_api_key', value='newkey').exists())

    def test_add_voice_api_key_update(self):
        response = self.client.post(reverse('add_voice_api_key'), json.dumps({'voice_api_key': 'updatedkey'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Utility.objects.filter(name='voice_api_key', value='updatedkey').exists())

    # api_setup view
    def test_api_setup_success_linux(self):
        self.mock_os_path_exists.side_effect = lambda path: path != self.env_file_path_in_views # .env does not exist
        self.mock_platform_system.return_value = "Linux"
        self.mock_subprocess_popen.return_value = MagicMock(pid=12345) # Mock the Popen object

        response = self.client.post(reverse('api_setup'), {'domain': 'http://localhost:8000'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['message'], 'Setup completed successfully.')
        self.mock_views_open.assert_called_with(self.env_file_path_in_views, "w")
        self.mock_subprocess_popen.assert_called_once()

    def test_api_setup_env_exists(self):
        self.mock_os_path_exists.side_effect = lambda path: path == self.env_file_path_in_views # .env exists
        response = self.client.post(reverse('api_setup'), {'domain': 'http://localhost:8000'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], '.env file already exists.')

    # get_current_version view
    @patch('data.views.sys.version_info')
    def test_get_current_version_success(self, mock_sys_version_info):
        mock_sys_version_info.major, mock_sys_version_info.minor, mock_sys_version_info.micro = 3, 10, 0
        local_v_data = json.dumps({"version": "1.0.0", "python_version": ["3.10 - 3.12"]})
        remote_v_data = {"version": "1.1.0", "release_date": "2023-01-01", "changelog": [], "python_version": ["3.10 - 3.12"]}
        
        # Configure mock_views_open for local version.json
        # It's tricky if other views also use open. Assuming this is the first targeted open.
        self.mock_views_open.side_effect = [
            mock_open(read_data=local_v_data).return_value, # For local version.json
            # Add more if other open calls are expected in this test flow
        ]

        self.mock_requests_get.return_value.status_code = 200
        self.mock_requests_get.return_value.json.return_value = remote_v_data

        response = self.client.get(reverse('get_current_version'))
        self.assertEqual(response.status_code, 200)
        json_resp = response.json()
        self.assertEqual(json_resp['version'], "1.0.0")
        self.assertEqual(json_resp['latest_version'], "1.1.0")
        self.assertTrue(json_resp['update_available'])
        self.assertTrue(json_resp['compatible_python'])
        self.mock_views_open.assert_any_call(os.path.join(self.mock_base_dir, 'version.json'), 'r', encoding='utf-8')

    def test_get_current_version_local_file_error(self):
        self.mock_views_open.side_effect = FileNotFoundError # Mock open for local version.json
        response = self.client.get(reverse('get_current_version'))
        self.assertEqual(response.status_code, 500)
        self.assertIn("Failed to read local version.json", response.json()['error'])

    # api_update view
    @patch('data.views.SCRIPT_PATH', new_callable=lambda: os.path.join('/fake/basedir', "scripts/update_script.sh"))
    def test_api_update_success_linux(self, mock_script_path_in_view):
        self.mock_platform_system.return_value = "Linux"
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        self.mock_subprocess_popen.return_value = mock_proc

        # This script_path is for the assertion, and should match the mocked SCRIPT_PATH in the view
        expected_script_path_for_chmod = mock_script_path_in_view

        response = self.client.get(reverse('api_update'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['process_id'], 12345)
        self.mock_subprocess_run.assert_called_with(["chmod", "+x", expected_script_path_for_chmod], check=True)
        self.mock_subprocess_popen.assert_called_with([expected_script_path_for_chmod], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)

    def test_api_update_windows_not_supported(self):
        self.mock_platform_system.return_value = "Windows"
        response = self.client.get(reverse('api_update'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], "Windows is not supported")

    # api_process view
    def test_api_process_running_with_log(self):
        # Mock process is running and log file exists with content
        self.mock_is_process_running.return_value = True
        from data.views import STATUS_FILE_PATH
        self.mock_os_path_exists.side_effect = lambda path: path == self.env_file_path_in_views or os.path.normpath(path) == os.path.normpath(STATUS_FILE_PATH)
        from unittest.mock import mock_open, patch as patcher
        with patcher('data.views.open', mock_open(read_data='log content')) as m:
            response = self.client.get(reverse('api_process', args=['123']))
            found = False
            for c in m.call_args_list:
                if c[0][0] == STATUS_FILE_PATH and c[0][1] == 'r':
                    found = True
            self.assertTrue(found, "open called with correct STATUS_FILE_PATH and mode")
        self.assertEqual(response.json(), {"status": "running", "log": "log content"})

    def test_api_process_completed_no_log_file(self):
        # Mock process is not running and log file does not exist
        self.mock_is_process_running.return_value = False
        self.mock_os_path_exists.side_effect = lambda path: path == self.env_file_path_in_views
        response = self.client.get(reverse('api_process', args=['123']))
        self.assertEqual(response.json(), {"status": "completed_or_not_found", "log": "Process is not running and no log file found."})

    # upload_file view
    # Moved import to the top of the file
    def test_upload_file_success_mp3(self):
        self.mock_os_path_exists.side_effect = lambda path: True # Assume dir exists for simplicity here
        file_content = b"mp3 data"
        uploaded_file = SimpleUploadedFile("test.mp3", file_content, content_type="audio/mpeg")
        response = self.client.post(reverse('upload_file'), {'file': uploaded_file})
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(Audio.objects.filter(name="test.mp3").exists())
        audio_obj = Audio.objects.get(name="test.mp3")
        self.assertEqual(os.path.normpath(audio_obj.path), os.path.normpath(os.path.join("audio/uploads", "test.mp3")))
        # Accept both slash and backslash by normalizing
        found = False
        for c in self.mock_views_open.call_args_list:
            if os.path.normpath(c[0][0]) == os.path.normpath(os.path.join("audio/uploads", "test.mp3")) and c[0][1] == "wb+":
                found = True
        self.assertTrue(found, "open called with correct normalized path and mode")

    def test_upload_file_invalid_extension(self):
        uploaded_file = SimpleUploadedFile("test.txt", b"text data", content_type="text/plain")
        response = self.client.post(reverse('upload_file'), {'file': uploaded_file})
        self.assertEqual(response.status_code, 400)
        # The error message in view is "อัพโหลดได้เฉพาะไฟล์ MP3 เท่านั้น!" but code allows .wav too.
        # Testing that it rejects .txt is valid.
        self.assertEqual(response.json()['error'], "อัพโหลดได้เฉพาะไฟล์ MP3 เท่านั้น!")

    def test_upload_file_creates_directory(self):
        # Patch makedirs to accept any kwargs
        from unittest.mock import ANY
        self.mock_os_path_exists.return_value = False
        upload_dir = "audio/uploads/"
        file_mock = SimpleUploadedFile("test.mp3", b"filecontent", content_type="audio/mp3")
        response = self.client.post(reverse('upload_file'), {"file": file_mock})
        # Accept makedirs with or without exist_ok
        self.mock_os_makedirs.assert_any_call(upload_dir)