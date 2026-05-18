"""read_positions.py — Live joint position reader for manual pose tuning.

Move the arm by hand while torque is disabled and watch the values update
in real time. When you find a good pose, hit Ctrl+C and the script prints
 the last reading in a copy-paste-friendly format for ACTION_MAP.

Run:
    cd ~/lerobot/examples/voice_arm
    python read_positions.py
"""

import time
import robot_arm


def fmt_obs(obs: dict) -> str:
    """Format observation as a compact single-line table."""
    if not obs:
        return "(no data)"
    parts = []
    for key in sorted(obs.keys()):
        if key.endswith(".pos"):
            name = key.replace(".pos", "")
            parts.append(f"{name:11s}:{obs[key]:6.1f}")
    return " | ".join(parts)


def print_captured_pose(obs: dict):
    """Print the last observation as an ACTION_MAP entry."""
    pos_items = {k: v for k, v in obs.items() if k.endswith(".pos")}
    if not pos_items:
        return
    print("\n📋  Last captured pose (copy-paste into ACTION_MAP):")
    print('    "my_pose": {')
    for key in sorted(pos_items.keys()):
        print(f'        "{key}": {pos_items[key]:.2f},')
    print("    },")


def main():
    print("=" * 72)
    print("  Live Joint Position Reader")
    print("  • Torque will be disabled so you can move the arm by hand.")
    print("  • Values update live below.")
    print("  • Press Ctrl+C to capture the last pose and disconnect.")
    print("=" * 72)

    arm = robot_arm.get_arm()

    if not arm.is_connected():
        print("[Reader] Arm not connected. Check ARM_PORT in config.env.")
        return

    # Disable torque so user can move joints freely
    try:
        arm._robot.bus.disable_torque()
        print("[Reader] Torque disabled — move the arm now.\n")
    except Exception as e:
        print(f"[Reader] Could not disable torque: {e}")
        return

    last_obs = {}
    try:
        while True:
            obs = arm.get_observation()
            last_obs = obs
            line = fmt_obs(obs)
            print(f"\r{line:<70}", end="", flush=True)
            time.sleep(0.15)
    except KeyboardInterrupt:
        print("\n\n[Reader] Stopping...")

    if last_obs:
        print_captured_pose(last_obs)

    # Re-enable torque before disconnecting so arm holds position
    try:
        arm._robot.bus.enable_torque()
        print("[Reader] Torque re-enabled.")
    except Exception as e:
        print(f"[Reader] Could not re-enable torque: {e}")

    arm.close()
    print("[Reader] Disconnected.")


if __name__ == "__main__":
    main()
