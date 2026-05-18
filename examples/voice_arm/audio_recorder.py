"""audio_recorder.py — records N seconds from the mic and returns WAV bytes.
Opens its own short-lived PyAudio stream so it doesn't conflict with
the wake-word detector (which pauses before calling this).
"""
import io
import wave
import pyaudio

import config


def record(seconds: int = config.RECORDING_SECONDS) -> bytes:
    """Record `seconds` of audio and return a WAV-formatted bytes object."""
    p = pyaudio.PyAudio()
    chunk = 1024
    total_frames = int(config.SAMPLE_RATE / chunk * seconds)

    print(f"[Recorder] Recording {seconds}s ...")
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=config.SAMPLE_RATE,
        input=True,
        input_device_index=config.MIC_INDEX,
        frames_per_buffer=chunk,
    )

    frames = []
    for _ in range(total_frames):
        data = stream.read(chunk, exception_on_overflow=False)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()
    print("[Recorder] Done")

    # Pack into WAV bytes (in-memory — no temp file needed)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(config.SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    return buf.getvalue()