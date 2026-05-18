"""config.py — loads all settings from config.env"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "config.env")

# Groq
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")

# Wake word
WAKEWORD_MODEL: str       = os.getenv("WAKEWORD_MODEL", "hey jarvis")
MIC_INDEX: int            = int(os.getenv("MIC_INDEX", 1))
WAKEWORD_THRESHOLD: float = float(os.getenv("WAKEWORD_THRESHOLD", 0.5))
WAKEWORD_COOLDOWN: float  = float(os.getenv("WAKEWORD_COOLDOWN", 2.0))

# Recording
RECORDING_SECONDS: int = int(os.getenv("RECORDING_SECONDS", 3))
SAMPLE_RATE: int       = int(os.getenv("SAMPLE_RATE", 16000))

# LLM
LLM_MODEL: str      = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", 128))

# STT
STT_MODEL: str    = os.getenv("STT_MODEL", "whisper-large-v3-turbo")
STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "en")

# TTS
TTS_MODEL: str = os.getenv("TTS_MODEL", "canopylabs/orpheus-v1-english")
TTS_VOICE: str = os.getenv("TTS_VOICE", "autumn")

# SO100 Robot Arm
ARM_PORT: str           = os.getenv("ARM_PORT", "/dev/ttyACM0")
ARM_ID: str             = os.getenv("ARM_ID", "my_awesome_follower_arm")
ARM_MOVE_DELAY: float   = float(os.getenv("ARM_MOVE_DELAY", 1.5))    # seconds to settle after a single pose
ARM_GESTURE_DELAY: float = float(os.getenv("ARM_GESTURE_DELAY", 0.4)) # seconds between gesture sequence steps

if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY is not set in config.env")