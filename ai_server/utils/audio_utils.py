import subprocess
import os

def preprocess_audio(input_path: str, output_path: str):
    """
    Converts any audio file to 16kHz mono WAV for WhisperX (automatically done by whisperx.load_audio)
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"{input_path} not found")

    command = [
        "ffmpeg",
        "-y",                 # overwrite output
        "-i", input_path,
        "-ar", "16000",       # sample rate
        "-ac", "1",           # mono
        output_path
    ]

    subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )

    return output_path
