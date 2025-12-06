# recorder.py
import sounddevice as sd
import soundfile as sf


def record_wav(filename="audio.wav", duration=5, samplerate=16000, channels=1):
    """Record audio and write to a WAV file. Returns the filename."""
    print(f"Recording for {duration} seconds...")
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels)
    sd.wait()
    # convert floats to 16-bit PCM automatically via soundfile
    sf.write(filename, recording, samplerate, subtype='PCM_16')
    return filename


if __name__ == '__main__':
    record_wav(duration=4)