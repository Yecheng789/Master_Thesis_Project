# BlueROV2 Fixed-Target Hook Retrieval

## Installation

Use Ubuntu 24.04, ROS 2 Jazzy, Python 3.12, colcon, and rosdep. Install
[acados](https://docs.acados.org/installation/index.html), including its
Python interface, shared libraries, and template renderer. NumPy, CasADi,
and `acados_template` must be importable by the Python interpreter used by
ROS. Install Micro XRCE-DDS Agent and QGroundControl separately.

For a new workspace:

```bash
mkdir -p /home/yecheng/bluerov_ws/src
git clone https://github.com/Yecheng789/Bluerov2_Glub.git \
  /home/yecheng/bluerov_ws/src/bluerov2_control
```

Place the PX4 message sources matching the deployed firmware at
`/home/yecheng/bluerov_ws/src/px4_msgs` before building. This repository does
not include PX4 firmware, acados, a MoCap driver, or recorded trial datasets.

With the vehicle DISARMED and control launches stopped, run the following
from a fresh Bash terminal. Initialize rosdep first if it has not been
configured on this computer.

```bash
cd /home/yecheng/bluerov_ws
source /opt/ros/jazzy/setup.bash

export ACADOS_SOURCE_DIR=/home/yecheng/acados
export LD_LIBRARY_PATH=/home/yecheng/acados/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}

rosdep update
rosdep install --from-paths src/bluerov2_control src/px4_msgs \
  --ignore-src --rosdistro jazzy --skip-keys python3-casadi -y

python3 -c "import numpy, casadi, acados_template"
colcon build --packages-select px4_msgs --symlink-install
source install/local_setup.bash
colcon build --packages-select bluerov2_control --symlink-install

source src/bluerov2_control/scripts/source_fixed_hook_real.bash
```

Stop if an import, build, or environment check fails. CasADi is installed
with the acados Python environment rather than through rosdep. For offline
analysis and tests, also install Matplotlib, pandas, and pytest.

## Configuration requirements

Commands use the lab paths `/home/yecheng/bluerov_ws` and
`/home/yecheng/acados`. For another installation, update path-dependent
settings in the environment helper and launch files before use.

| Setting | Required configuration |
| --- | --- |
| ROS / RMW | Jazzy / `rmw_fastrtps_cpp` |
| PX4 messages | Firmware-matched `src/px4_msgs`; this fixed-target profile checks ACK/Status versions `0 / 1` |
| Glub namespace / raw pose | `/glub` / `/mocap/glub/pose` |
| Splash namespace / raw pose | `/splash` / `/mocap/splash/pose` |
| MAVLink system / component | Defaults `3 / 1`; verify against the vehicle |
| MoCap world / body convention | Defaults NED / FRD; verify physical axes and mounting |
| Dynamics | `fossen_real`, `standard` |
| Raw MoCap pool bounds | `0 9 -2.5 2.5 0 3` m in `xmin xmax ymin ymax zmin zmax` order |
| Inward boundary margin | `0.25 m` |
| Target | Explicit, validated robot-specific JSON passed as `target_config` |
| Pre-hook reference | `0.50 m` behind the recorded horizontal heading, at Hook depth |
| Approach / forward / retreat reference speeds | `0.06 / 0.09 / 0.09 m/s` |
| NMPC / A* monitor | Nominally `25 / 2 Hz` |
| Normalized thrust / torque limits | `0.12 / 0.02` |
| Hook confirmation | Operator `H` in `WAIT_HOOK` starts retreat; no automatic wait timeout |

Source the environment helper in each ROS terminal. Do not source a different
PX4 workspace afterward. If the firmware uses different message versions,
resolve the firmware/interface compatibility before proceeding; changing topic
suffixes or bypassing the helper is not a valid substitute.

Live MoCap and PX4 BODY_FRD angular-rate feedback are required. Synchronize
the measurement and control clocks. Verify pool coordinates, target provenance,
state freshness, and manual takeover before enabling motion. Record a new
target after moving the box or changing the rigid-body definition or mounting.

A* checks configured bounds and static obstacles only. Supply measured
obstacles through `prehook_static_obstacles_ned_xyxy`; the default list is
empty. The planner does not detect people, tethers, or moving obstacles.

Run only one robot profile and one control stack at a time. Do not combine
this pipeline with `stabilized_control_real.launch.py`, a standalone
Offboard node, or another controller. Glub and Splash share operator-permission
topics. Keep QGC, manual takeover, and an emergency stop available.

## Reproduction

### 1. Start communication and recording

Follow the complete procedure for the selected robot, including target
recording, preflight checks, Offboard permission, manual arming, and shutdown:

- [Glub operator guide](experiments/payload_retrieval/FIXED_HOOK_POSE_VALIDATION_ZH.md)
- [Splash operator guide](experiments/payload_retrieval/SPLASH_FIXED_HOOK_ZH.md)

If no DDS Agent is already running, and PX4 is configured for this computer
on UDP port 8888, start one in a dedicated terminal:

```bash
micro-xrce-dds-agent udp4 -p 8888
```

Open QGC in another terminal:

```bash
cd /home/yecheng/Downloads
./QGroundControl-x86_64.AppImage
```

Before starting control, record the target using the selected operator guide
and start [rosbag and external video recording](experiments/payload_retrieval/README.md#record-data).
Manually position the robot at a safe starting point, then DISARM.

### 2. Launch the selected robot profile

Complete the guide's frame, target, feedback, and publisher checks first.
In a dedicated terminal, choose one robot and provide its validated target:

```bash
cd /home/yecheng/bluerov_ws
source src/bluerov2_control/scripts/source_fixed_hook_real.bash

read -r -p 'Robot profile (glub or splash): ' ROBOT_NAME
read -r -p 'Validated target JSON (absolute path): ' TARGET_CFG

case "$ROBOT_NAME" in
  glub) FIXED_HOOK_LAUNCH=fixed_hook_pose_validation.launch.py ;;
  splash) FIXED_HOOK_LAUNCH=fixed_hook_pose_validation_splash.launch.py ;;
  *) FIXED_HOOK_LAUNCH= ;;
esac

if [[ -n "$FIXED_HOOK_LAUNCH" && "$TARGET_CFG" == /* && -r "$TARGET_CFG" ]]; then
  ros2 launch bluerov2_control "$FIXED_HOOK_LAUNCH" \
    target_config:="$TARGET_CFG"
else
  echo 'Select glub or splash and a readable absolute target path.'
fi
```

The launch starts the EKF, odometry adapter, NMPC, CSV logger, and Offboard
manager. It does not arm the vehicle, request Offboard, or enable motion.
Verify the printed target, pre-hook point, operating bounds, and model.
Complete the operator guide's post-launch checks while DISARMED.

### 3. Enable and supervise the trial

Use the selected guide's separate permission commands in this order:

1. Clear `mission_enable` and `offboard_request_enable`.
2. Request Offboard only after preflight passes; require an accepted mode
   command ACK and actual Offboard feedback in PX4 and QGC.
3. Prepare the Hook-confirmation terminal below, but do not press H yet.
4. ARM manually in QGC. Verify Armed/Offboard feedback, healthy state,
   active recording, and a clear travel corridor.
5. Mark the trial start and publish `mission_enable=true` as shown in the guide.

Keep the Hook-confirmation client in its own foreground terminal:

```bash
source /home/yecheng/bluerov_ws/src/bluerov2_control/scripts/source_fixed_hook_real.bash
ros2 run bluerov2_control confirm_hook_keyboard
```

After `WAIT_HOOK` is reported, wait at least `0.25 s` and visually verify
engagement before pressing H. Accepted confirmation starts `GO_BACK`.
`COMPLETE` holds at pre-hook; it does not automatically DISARM.

For a normal stop, DISARM in QGC and verify that the thrusters have stopped.
Clear both permission gates using the guide's commands, leave Offboard in
QGC, stop the control launch, and finally stop rosbag. Setting Offboard
request permission to false does not itself switch the active PX4 mode.
For an unsafe motion or control failure, use the verified manual takeover
or emergency stop immediately. Zero thrust is not position holding.

### 4. Analyze data and run offline tests

Use the [experiment reproduction guide](experiments/payload_retrieval/README.md)
for trial analysis and paper-figure commands.

Run functional tests from the workspace root, with no live control launch:

```bash
cd /home/yecheng/bluerov_ws
source src/bluerov2_control/scripts/source_fixed_hook_real.bash
python3 -m pytest -q src/bluerov2_control/test \
  --ignore=src/bluerov2_control/test/test_copyright.py \
  --ignore=src/bluerov2_control/test/test_flake8.py \
  --ignore=src/bluerov2_control/test/test_pep257.py
```

Copyright and style checks are separate. The recorded-baseline audit requires
the archived Direct-front dataset and is skipped when it is unavailable.
Offline tests do not replace supervised hardware validation.
