# Placeholder for voice-arm pipeline
# Replaces LeKiwi's pipeline for arm-specific processing
"""pipeline.py — Voice assistant + SO100 arm controller pipeline.

Full flow:
  [IDLE] Wake word detected
      → pause wake word detector
      → record N seconds
      → STT  (Groq Whisper)
      → LLM  → returns { speech, action }
      → TTS  speaks the reply
      → Arm  → executes the action on SO100 follower
      → resume wake word detector
      → [IDLE]

Run with:
    cd ~/lerobot/examples/voice_arm
    python pipeline.py
"""
import threading
import time

import config
import wakeword as ww_module
import audio_recorder
import stt
import llm
import tts
import robot_arm


class Pipeline:
    def __init__(self):
        self._detector = ww_module.WakeWordDetector()
        self._detector.on_detected = self._on_wakeword
        self._arm = robot_arm.get_arm()
        self._processing = False
        self._lock = threading.Lock()

    # ── entry point ──────────────────────────────────────────────────────────

    def run(self):
        print("=" * 54)
        print("  SO100 Arm Voice Controller — Ready")
        print(f"  Wake word  : {config.WAKEWORD_MODEL}")
        print(f"  LLM model  : {config.LLM_MODEL}")
        print(f"  STT model  : {config.STT_MODEL}")
        print(f"  TTS voice  : {config.TTS_VOICE}")
        print(f"  Arm port   : {config.ARM_PORT or 'DISABLED'}  id={config.ARM_ID!r}")
        print("=" * 54)
        self._detector.start()
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[Pipeline] Shutting down ...")
            self._arm.close()
            self._detector.stop()

    # ── wake word callback ────────────────────────────────────────────────────

    def _on_wakeword(self, confidence: float):
        with self._lock:
            if self._processing:
                return
            self._processing = True
        threading.Thread(target=self._pipeline_step, daemon=True).start()

    # ── main pipeline ─────────────────────────────────────────────────────────

    def _pipeline_step(self):
        try:
            # 1. Pause wake word detector so mic is free
            self._detector.pause()

            # 2. Record audio
            wav_bytes = audio_recorder.record(config.RECORDING_SECONDS)

            # 3. STT — bail early on silence / noise
            text = stt.transcribe(wav_bytes)
            if not text:
                print("[Pipeline] Nothing heard — returning to idle")
                return

            # 4. LLM — returns { speech, action }
            result = llm.chat(text)
            speech = result.get("speech", "")
            action = result.get("action", "none")

            # 5. TTS — speak the reply so user gets feedback immediately
            if speech:
                tts.speak(speech)

            # 6. Arm — execute the action AFTER speech finishes
            if action and action != "none":
                success = self._arm.send_action(action)
                if not success:
                    print(f"[Pipeline] Failed to send arm action: {action!r}")

        except Exception as e:
            print(f"[Pipeline] Error: {e}")

        finally:
            self._processing = False
            self._detector.resume()


if __name__ == "__main__":
    Pipeline().run()