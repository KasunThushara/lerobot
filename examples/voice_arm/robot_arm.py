"""robot_arm.py — SO100 follower arm controller.

Calibration file is auto-loaded by SO100Follower from:
  ~/.cache/huggingface/lerobot/calibration/robots/so_follower/<ARM_ID>.json

Normalized value ranges (after calibration):
  Body joints (shoulder_pan, shoulder_lift, elbow_flex,
               wrist_flex, wrist_roll):  -100 … +100
  gripper:                                  0 … 100  (0=closed, 100=open)

ACTION_MAP supports two entry types:
  dict       → single pose, sent once then waits ARM_MOVE_DELAY
  list[dict] → sequence; each step waits ARM_GESTURE_DELAY (faster, good for gestures)
               Every step MUST include ALL 6 joints — partial dicts can cause errors.
"""

import time
from typing import Any

from lerobot.robots.so_follower import SO100Follower, SO100FollowerConfig

import config


# ── Shared pose preset ────────────────────────────────────────────────────────
# All joints at zero, gripper half-open. Used as a safe base for _pose().
_HOME = {
    "shoulder_pan.pos":  0.29,
    "shoulder_lift.pos": -99.00,
    "elbow_flex.pos":    99.19,
    "wrist_flex.pos":    0.0,
    "wrist_roll.pos":    76.25,
    "gripper.pos":      1.25,
}


def _pose(**overrides) -> dict:
    """Return a copy of _HOME with any joints overridden."""
    p = dict(_HOME)
    p.update(overrides)
    return p


# ── Action map ────────────────────────────────────────────────────────────────
# Tune the numbers here by running:
#   python examples/manual_control_follower.py --port /dev/ttyACM0
# and observing what normalized values match the pose you want physically.
#
# Your calibration ranges (for reference while tuning):
#   shoulder_pan  : 760 – 3157   (homing_offset  1871)
#   shoulder_lift : 883 – 3280   (homing_offset -1771)
#   elbow_flex    : 950 – 3168   (homing_offset  1656)
#   wrist_flex    : 659 – 2975   (homing_offset  -957)
#   wrist_roll    :   0 – 4095   (full rotation — use carefully)
#   gripper       : 2041 – 3485  (0 = closed, 100 = open)

ACTION_MAP: dict[str, Any] = {

    # ── Gripper only ──────────────────────────────────────────────────────────
    "gripper_open":  _pose(**{"gripper.pos": 100.0}),
    "gripper_half":  _pose(**{"gripper.pos":  50.0}),
    "gripper_close": _pose(**{"gripper.pos":   0.0}),

    # ── Full poses ────────────────────────────────────────────────────────────
    "home": _HOME,

    "pickup_mode": _pose(
        **{
            # Arm tilts forward and down, gripper wide open ready to grasp.
            # ⚠  Tune these values to match your table height and workspace.
            "shoulder_pan.pos":  0.54,
            "shoulder_lift.pos": 2.54,
            "elbow_flex.pos":    4.33,
            "wrist_flex.pos":    84.63,
            "wrist_roll.pos":    0.02,
            "gripper.pos":      1.25,
        }
    ),

    "turn_around": _pose(
        **{
            # Rotates base ~80% to the right. Change to -80.0 to turn left.
            "shoulder_pan.pos": 80.0,
        }
    ),

    # ── Gesture sequence: wave hi ─────────────────────────────────────────────
    # list[dict] → runs with ARM_GESTURE_DELAY between steps (fast).
    # Every step includes ALL 6 joints to avoid partial-spec errors.
    "wave_hi": [
        # 1. Raise arm up
        _pose(**{
            "shoulder_lift.pos": -70.0,
            "elbow_flex.pos":    -30.0,
            "wrist_flex.pos":      0.0,
            "gripper.pos":        50.0,
        }),
        # 2-5. Wave wrist back and forth
        _pose(**{"shoulder_lift.pos": -70.0, "elbow_flex.pos": -30.0, "wrist_flex.pos":  60.0, "gripper.pos": 50.0}),
        _pose(**{"shoulder_lift.pos": -70.0, "elbow_flex.pos": -30.0, "wrist_flex.pos": -60.0, "gripper.pos": 50.0}),
        _pose(**{"shoulder_lift.pos": -70.0, "elbow_flex.pos": -30.0, "wrist_flex.pos":  60.0, "gripper.pos": 50.0}),
        _pose(**{"shoulder_lift.pos": -70.0, "elbow_flex.pos": -30.0, "wrist_flex.pos": -60.0, "gripper.pos": 50.0}),
        # 6. Return to home
        _HOME,
    ],
}


# ── Robot arm class ───────────────────────────────────────────────────────────

class RobotArm:
    def __init__(self):
        self._robot: SO100Follower | None = None
        self._connected = False
        self._connect()

    def _connect(self):
        if not config.ARM_PORT:
            print("[Arm] ARM_PORT not set — arm commands disabled")
            return
        try:
            arm_config = SO100FollowerConfig(
                port=config.ARM_PORT,
                id=config.ARM_ID,
            )
            self._robot = SO100Follower(arm_config)
            self._robot.connect()
            self._connected = True
            print(f"[Arm] Connected on {config.ARM_PORT} (id={config.ARM_ID!r})")
        except Exception as e:
            print(f"[Arm] Could not connect: {e}")
            self._robot = None
            self._connected = False

    def is_connected(self) -> bool:
        return self._connected and self._robot is not None

    def send_action(self, action: str) -> bool:
        if not action or action == "none":
            return True

        targets = ACTION_MAP.get(action)
        if targets is None:
            print(f"[Arm] Unknown action: {action!r}")
            return False

        if not self.is_connected():
            print(f"[Arm] NOT connected — would have sent: {action!r}")
            return False

        try:
            if isinstance(targets, dict):
                # ── Single pose ──────────────────────────────────────────────
                print(f"[Arm] Pose: {action!r}")
                self._robot.send_action(targets)
                time.sleep(config.ARM_MOVE_DELAY)
                return True

            if isinstance(targets, list):
                # ── Gesture sequence ─────────────────────────────────────────
                print(f"[Arm] Sequence: {action!r} ({len(targets)} steps)")
                for i, step in enumerate(targets, 1):
                    print(f"[Arm]   step {i}/{len(targets)}")
                    self._robot.send_action(step)
                    # Last step gets full move delay so arm settles at final pose;
                    # intermediate steps use the faster gesture delay.
                    delay = config.ARM_MOVE_DELAY if i == len(targets) else config.ARM_GESTURE_DELAY
                    time.sleep(delay)
                return True

        except Exception as e:
            print(f"[Arm] send_action error: {e}")
            return False

        return False

    def get_observation(self) -> dict:
        if not self.is_connected():
            return {}
        try:
            return self._robot.get_observation()
        except Exception as e:
            print(f"[Arm] get_observation error: {e}")
            return {}

    def close(self):
        if self._robot and self._connected:
            try:
                self._robot.disconnect()
                print("[Arm] Disconnected")
            except Exception as e:
                print(f"[Arm] Disconnect error: {e}")
        self._connected = False


# ── Singleton ─────────────────────────────────────────────────────────────────
_arm: RobotArm | None = None


def get_arm() -> RobotArm:
    global _arm
    if _arm is None:
        _arm = RobotArm()
    return _arm