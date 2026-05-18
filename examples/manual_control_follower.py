#!/usr/bin/env python
"""
Manual control script for SO100 follower arm.

This script shows how to control the follower arm directly with code,
using your existing calibration file.

Usage:
    python examples/manual_control_follower.py --port /dev/ttyACM0

To find your port, run:
    lerobot-find-port
"""

import argparse
import time
from pathlib import Path

from lerobot.robots.so_follower import SO100Follower, SO100FollowerConfig


def main():
    parser = argparse.ArgumentParser(description="Manually control SO100 follower arm")
    parser.add_argument(
        "--port",
        type=str,
        default="/dev/ttyACM0",
        help="Serial port of the follower arm (e.g. /dev/ttyACM0, /dev/ttyACM1)",
    )
    parser.add_argument(
        "--id",
        type=str,
        default="my_awesome_follower_arm",
        help="Robot ID (used to load the calibration file)",
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # 1. Create robot configuration
    # ------------------------------------------------------------------
    # The calibration file is loaded automatically from:
    #   ~/.cache/huggingface/lerobot/calibration/robots/so_follower/<id>.json
    #
    # Your file is already at:
    #   /home/kasun/.cache/huggingface/lerobot/calibration/robots/so_follower/my_awesome_follower_arm.json
    #
    # So we only need to set the correct 'id'.
    config = SO100FollowerConfig(
        port=args.port,
        id=args.id,
        # If you ever need to use a custom calibration location, uncomment below:
        # calibration_dir=Path("/home/kasun/.cache/huggingface/lerobot/calibration/robots/so_follower"),
    )

    robot = SO100Follower(config)

    # ------------------------------------------------------------------
    # 2. Connect to the robot
    # ------------------------------------------------------------------
    print(f"Connecting to follower arm on {args.port}...")
    robot.connect()
    print("Connected!")

    # Read current positions
    obs = robot.get_observation()
    print("\nCurrent joint positions (normalized):")
    for key, val in obs.items():
        if key.endswith(".pos"):
            print(f"  {key}: {val:.2f}")

    try:
        # ==============================================================
        # METHOD A: High-level control with send_action (NORMALIZED values)
        # ==============================================================
        # For body joints:  -100 to 100  (or degrees if use_degrees=True)
        # For gripper:       0 to 100    (0 = closed, 100 = open)
        print("\n--- Method A: Normalized control via send_action ---")

        action = {
            "shoulder_pan.pos": 0.0,
            "shoulder_lift.pos": 0.0,
            "elbow_flex.pos": 0.0,
            "wrist_flex.pos": 0.0,
            "wrist_roll.pos": 0.0,
            "gripper.pos": 50.0,  # 50% open
        }
        print(f"Sending action: {action}")
        robot.send_action(action)
        time.sleep(1.0)

        # ==============================================================
        # METHOD B: Low-level control with RAW motor values
        # ==============================================================
        # Use normalize=False to bypass calibration scaling and write
        # directly to the motor registers.
        #
        # From your calibration file:
        #   gripper range_min = 2041
        #   gripper range_max = 3485
        #
        # So 2000 is just slightly outside the calibrated minimum.
        # The motor will clamp it to its hardware limit.
        print("\n--- Method B: Raw motor control via bus.write ---")

        # Move gripper to raw position 2000
        print("Setting gripper Goal_Position to raw value 2000...")
        robot.bus.write("Goal_Position", "gripper", 2000, normalize=False)
        time.sleep(1.0)

        # Read back the actual raw position
        raw_pos = robot.bus.read("Present_Position", "gripper", normalize=False)
        print(f"Gripper raw Present_Position: {raw_pos}")

        # You can also set other joints with raw values:
        # robot.bus.write("Goal_Position", "shoulder_pan", 2048, normalize=False)

        # ==============================================================
        # METHOD C: Batch raw writes with sync_write
        # ==============================================================
        print("\n--- Method C: Batch raw control via bus.sync_write ---")

        robot.bus.sync_write(
            "Goal_Position",
            {
                "shoulder_pan": 2048,
                "shoulder_lift": 2048,
                "elbow_flex": 2048,
                "wrist_flex": 2048,
                "wrist_roll": 2048,
                "gripper": 2000,
            },
            normalize=False,
        )
        print("Sent raw Goal_Position to all motors.")
        time.sleep(1.0)

        # Read all raw positions at once
        raw_positions = robot.bus.sync_read("Present_Position", normalize=False)
        print("Current raw positions:")
        for motor, pos in raw_positions.items():
            print(f"  {motor}: {pos}")

        print("\nDone! Disconnecting...")

    finally:
        # ------------------------------------------------------------------
        # 3. Always disconnect to disable torque and close the port safely
        # ------------------------------------------------------------------
        robot.disconnect()
        print("Disconnected.")


if __name__ == "__main__":
    main()
