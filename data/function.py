from pydub import AudioSegment

def get_audio_length(file_path):
    try:
        audio = AudioSegment.from_file(file_path)  # Works with MP3, WAV, etc.
        return len(audio) / 1000  # Convert milliseconds to seconds
    except Exception as e:
        print(f"Error reading audio file: {e}")
        return 0