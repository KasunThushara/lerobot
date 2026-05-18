#!/usr/bin/env python

import time
from lerobot.robots.so_follower import SO100Follower, SO100FollowerConfig

# Create config
config = SO100FollowerConfig(
    port="/dev/ttyACM0",
    id="my_awesome_follower_arm",
)

# Create robot
robot = SO100Follower(config)

print("Connecting...")
robot.connect()
print("Connected!")

try:
    # ----------------------------------------
    # Open gripper (100%)
    # ----------------------------------------
    print("Opening gripper...")
    robot.send_action({
        "gripper.pos": 100.0
    })
    time.sleep(2)

    # ----------------------------------------
    # Half close
    # ----------------------------------------
    print("Half close...")
    robot.send_action({
        "gripper.pos": 50.0
    })
    time.sleep(2)

    # ----------------------------------------
    # Fully close
    # ----------------------------------------
    print("Closing gripper...")
    robot.send_action({
        "gripper.pos": 0.0
    })
    time.sleep(2)

finally:
    robot.disconnect()
    print("Disconnected")