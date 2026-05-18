# Placeholder for LLm prompts and helpers for arm control
# Contains arm-specific prompting logic
"""llm.py — Text generation via Groq LLM.

Returns structured JSON so the pipeline knows:
  1. What to SAY  (speech)
  2. What to DO   (arm action)

Response format (always JSON):
{
  "speech": "Opening the gripper!",
  "action": "gripper_open"    // see ACTION_MAP in robot_arm.py, or "none"
}
"""
import json
from groq import Groq

import config

_client = Groq(api_key=config.GROQ_API_KEY)
_history: list[dict] = []

# ── System prompt ──────────────────────────────────────────────────────────────
_ARM_SYSTEM_PROMPT = """
You are a voice controller for a SO100 robotic arm. The user speaks commands aloud.
You must respond ONLY with a JSON object — no extra text, no markdown.

JSON format:
{
  "speech": "<short, friendly spoken reply — 1-2 sentences>",
  "action": "<arm action or 'none'>"
}

Valid actions:
  gripper_open    = open the gripper fully (100%)
  gripper_half    = open the gripper halfway (50%)
  gripper_close   = close the gripper fully (0%)
  home            = return all joints to a neutral resting pose
  pickup_mode     = move arm into a ready-to-pick-up pose (gripper open, arm forward)
  turn_around     = rotate the base to look to one side
  wave_hi         = raise the arm and wave at people, then return to neutral
  none            = no physical action needed

Trigger rules:
  - "open" / "release" / "let go" / "drop"                → gripper_open
  - "half" / "halfway" / "partial"                         → gripper_half
  - "close" / "grab" / "grip" / "hold"                    → gripper_close
  - "home" / "reset" / "go back" / "rest"                 → home
  - "pick up" / "pickup mode" / "get ready to grab"       → pickup_mode
  - "turn around" / "look left" / "look right" / "spin"   → turn_around
  - "say hi" / "wave" / "hello" / "greet"                 → wave_hi
  - Questions or unrelated speech                          → none

Examples:
  User: "open the gripper"            → {"speech": "Opening the gripper!", "action": "gripper_open"}
  User: "grab it"                     → {"speech": "Closing the gripper.", "action": "gripper_close"}
  User: "halfway"                     → {"speech": "Setting gripper to 50 percent.", "action": "gripper_half"}
  User: "release"                     → {"speech": "Releasing!", "action": "gripper_open"}
  User: "go to pick up mode"          → {"speech": "Getting into pick-up position.", "action": "pickup_mode"}
  User: "can you turn around"         → {"speech": "Turning around now.", "action": "turn_around"}
  User: "say hi to people"            → {"speech": "Hello everyone!", "action": "wave_hi"}
  User: "wave at the camera"          → {"speech": "Hi there!", "action": "wave_hi"}
  User: "go home"                     → {"speech": "Returning to home position.", "action": "home"}
  User: "what can you do?"            → {"speech": "I can open and close the gripper, wave, turn around, or get into pick-up mode!", "action": "none"}

If the command is unclear, reply helpfully in speech and set action to none.
Always respond ONLY with the JSON object.
""".strip()


def chat(user_text: str) -> dict:
    """
    Send user_text to LLM and return parsed dict:
      { "speech": str, "action": str }
    Falls back to a safe default on parse error.
    """
    _history.append({"role": "user", "content": user_text})

    messages = [{"role": "system", "content": _ARM_SYSTEM_PROMPT}] + _history

    print(f"[LLM] Input: {user_text!r}")

    completion = _client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=messages,
        max_tokens=config.LLM_MAX_TOKENS,
        temperature=0.3,
        stream=False,
    )

    raw = completion.choices[0].message.content.strip()
    print(f"[LLM] Raw response: {raw}")

    result = _parse_response(raw)
    _history.append({"role": "assistant", "content": raw})

    # Keep history from growing unbounded
    if len(_history) > 20:
        _history.pop(0)
        _history.pop(0)

    print(f"[LLM] Speech: {result['speech']!r}  Action: {result['action']}")
    return result


def _parse_response(raw: str) -> dict:
    """Parse LLM JSON response with fallback."""
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(clean)
        return {
            "speech": str(data.get("speech", "Done.")),
            "action": str(data.get("action", "none")).lower(),
        }
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[LLM] JSON parse error: {e} — using fallback")
        return {
            "speech": raw[:200] if raw else "I didn't understand that.",
            "action": "none",
        }


def reset_history():
    """Clear conversation history."""
    _history.clear()