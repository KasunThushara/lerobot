"""test_poses.py — safely try out the new arm poses one by one.

Run this from the voice_arm folder:
    cd ~/lerobot/examples/voice_arm
    python test_poses.py

Press ENTER to move to the next pose, or type 's' + ENTER to skip.
Type 'q' + ENTER at any prompt to quit and disconnect.
"""

import robot_arm


def main():
    arm = robot_arm.get_arm()

    if not arm.is_connected():
        print("[Test] Arm is not connected. Check ARM_PORT in config.env.")
        return

    poses = [
        ("home", "Return to neutral (all joints zero)"),
        ("pickup_mode", "Pick-up pose — arm forward, gripper open"),
        ("turn_around", "Rotate base to the side"),
        ("wave_hi", "Wave sequence (raise arm + wave wrist)"),
    ]

    print("=" * 60)
    print("  Pose tester — move through each new action safely")
    print("  Commands: [Enter]=run  s=skip  q=quit")
    print("=" * 60)

    for action, description in poses:
        print(f"\n  Next: '{action}' — {description}")
        choice = input("  Run this pose? [Enter/s/q]: ").strip().lower()

        if choice == "q":
            print("  Quitting...")
            break
        if choice == "s":
            print("  Skipped.")
            continue

        print(f"  → Running {action!r}")
        ok = arm.send_action(action)
        if ok:
            obs = arm.get_observation()
            print(f"  → Current positions: {obs}")
        else:
            print(f"  → FAILED to run {action!r}")

    print("\n  Returning to home before disconnect...")
    arm.send_action("home")
    arm.close()
    print("  Done.")


if __name__ == "__main__":
    main()
