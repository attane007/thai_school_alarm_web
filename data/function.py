
import wave

def get_wav_length(file_path):
    with wave.open(file_path, 'rb') as wav_file:
        # Get the number of frames and the frame rate
        num_frames = wav_file.getnframes()
        frame_rate = wav_file.getframerate()
        # Calculate the duration in seconds
        duration = num_frames / float(frame_rate)
        return duration