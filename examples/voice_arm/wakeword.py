"""wakeword.py — listens for the wake word using openwakeword.
Runs in its own thread. Calls on_detected(confidence) when triggered.
Can be paused/resumed so the mic is free during recording + playback.
"""
import time
import threading
import numpy as np
import pyaudio
from openwakeword.model import Model

import config


class WakeWordDetector:
    def __init__(self):
        self._p = pyaudio.PyAudio()
        self._model = Model(
            wakeword_models=[config.WAKEWORD_MODEL],
            vad_threshold=0.5
        )
        self._chunk_size = int(config.SAMPLE_RATE * 0.08)   # 80 ms frames
        self._stream: pyaudio.Stream | None = None
        self._running = False
        self._paused = threading.Event()
        self._paused.set()                                   # not paused by default
        self._thread: threading.Thread | None = None
        self.on_detected = None                              # set from pipeline
        self._last_trigger = 0.0

    # ── public controls ──────────────────────────────────────────────────────

    def start(self):
        """Open mic and begin listening in a background thread."""
        self._running = True
        self._open_stream()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[WakeWord] Listening for '{config.WAKEWORD_MODEL}' ...")

    def pause(self):
        """Release the mic completely so audio_recorder can open it."""
        self._paused.clear()
        time.sleep(0.05)        # let the loop iteration finish before closing
        self._close_stream()    # ← FREE the device
        print("[WakeWord] Paused — mic released")

    def resume(self):
        """Reopen the mic and resume detection."""
        self._model.reset()     # clear stale internal state
        self._open_stream()     # ← REACQUIRE the device
        self._paused.set()
        print(f"[WakeWord] Resumed — listening for '{config.WAKEWORD_MODEL}' ...")

    def stop(self):
        """Shut down permanently."""
        self._running = False
        self._paused.set()                                   # unblock loop if paused
        self._close_stream()
        if self._thread:
            self._thread.join(timeout=3)
        self._p.terminate()
        print("[WakeWord] Stopped")

    # ── private ──────────────────────────────────────────────────────────────

    def _open_stream(self):
        self._stream = self._p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=config.SAMPLE_RATE,
            input=True,
            input_device_index=config.MIC_INDEX,
            frames_per_buffer=self._chunk_size,
        )

    def _close_stream(self):
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def _loop(self):
        while self._running:
            self._paused.wait()                              # block when paused
            if not self._running:
                break
            if self._stream is None:                        # safety: not open yet
                time.sleep(0.02)
                continue

            try:
                raw = self._stream.read(self._chunk_size, exception_on_overflow=False)
            except Exception as e:
                print(f"[WakeWord] Stream read error: {e}")
                time.sleep(0.05)
                continue

            audio = np.frombuffer(raw, dtype=np.int16)
            predictions = self._model.predict(audio)
            confidence = predictions.get(config.WAKEWORD_MODEL, 0.0)

            now = time.time()
            if (
                confidence > config.WAKEWORD_THRESHOLD
                and (now - self._last_trigger) > config.WAKEWORD_COOLDOWN
            ):
                self._last_trigger = now
                print(f"[WakeWord] Detected! confidence={confidence:.2f}")
                if self.on_detected:
                    self.on_detected(confidence)