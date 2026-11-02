# Fixed-Target Experiment Reproduction

## Installation

Build `px4_msgs` and `bluerov2_control` using the
[package installation instructions](../../README.md#installation).
Install Matplotlib and pandas for plots, and pytest for functional tests.
Load the fixed-target environment in each ROS terminal:

```bash
source /home/yecheng/bluerov_ws/src/bluerov2_control/scripts/source_fixed_hook_real.bash
```

## Configuration requirements

| Input or output | Requirement |
| --- | --- |
| Glub target source | A validated raw `/mocap/glub/pose` recording |
| Splash target source | A validated raw `/mocap/splash/pose` recording, or the permitted unchanged-body rename manifest |
| State feedback | Fresh MoCap/EKF pose and PX4 BODY_FRD angular rates |
| Frames and pool | Verified NED/FRD conversion, pool origin, measured bounds, and obstacle clearance |
| Control ownership | One robot profile and one control stack; manual takeover available |
| Automatic CSV output | `/home/yecheng/bluerov_ws/bluerov2_payload_retrieval_trials` |
| Rosbag output below | `/home/yecheng/bluerov_ws/fixed_hook_bags` |

Neither launch selects a target automatically. Do not copy target quaternions
between robots or edit a recording's provenance to make it pass validation.
Re-record after changes to the box position, rigid-body geometry, axes, or
mounting. The optional Splash rename manifest is valid only under the
conditions in the [Splash guide](SPLASH_FIXED_HOOK_ZH.md); a Glub-to-Splash
target transfer must not be used.

The guarded launch already starts the CSV logger. Do not launch another
controller or legacy data-collection stack alongside it. Each trial directory
contains `samples.csv`, `events.csv`, and `metadata.json`.
Record configuration, calibration, payload, operator, and environmental
conditions using the [metadata template](config/trial_metadata_template.json).

Paper-figure reproduction requires the original three trial directories,
including their CSV files and metadata, under
`/home/yecheng/bluerov_ws/bluerov2_payload_retrieval_trials`:

- `retrieval_box_near_the_front_success`
- `retrieval_right_side_of_the_box_success`
- `retrieval_directly_in_front_of_the_box_success`

These datasets are not included in a source-only checkout. Preserve the
associated [phase annotations](../../scripts/three_success_trial_annotations.json)
and [controller-event evidence](../../scripts/three_success_controller_event_evidence.txt).

## Reproduction

### Record a target and run control

Follow the [Glub](FIXED_HOOK_POSE_VALIDATION_ZH.md) or
[Splash](SPLASH_FIXED_HOOK_ZH.md) operator guide for the complete terminal
sequence. Keep automatic control stopped during manual positioning and target
recording. For Glub:

```bash
cd /home/yecheng/bluerov_ws
source src/bluerov2_control/scripts/source_fixed_hook_real.bash

TARGET_CFG="$PWD/src/bluerov2_control/experiments/payload_retrieval/config/hooked_box_target_pose_glub_$(date +%Y%m%d_%H%M%S).json"

if ros2 run bluerov2_control record_mocap_target_pose \
  --topic /mocap/glub/pose \
  --message-type pose \
  --samples 160 \
  --timeout-sec 20 \
  --max-message-age-sec 0.20 \
  --output-file "$TARGET_CFG"
then
  python3 -m json.tool "$TARGET_CFG"
  echo "Validated target file: $TARGET_CFG"
else
  unset TARGET_CFG
  echo 'Target validation failed; do not start control with this recording.'
fi
```

Require `validation.passed=true` and the correct source topic. Keep the box
fixed after recording and save the printed absolute path. For Splash, use
its own target-recording command in the Splash guide.

Start recording, manually move to the starting position, DISARM, and launch
the selected profile with the validated target. Complete preflight before
requesting Offboard, arming manually, and enabling motion. In `WAIT_HOOK`,
the operator confirms physical engagement with H; the robot then retreats.
Follow the guide's shutdown procedure before stopping the recorder.

### Record data

Use this in a dedicated terminal before starting the control launch. Select
the same robot profile as the controller:

```bash
cd /home/yecheng/bluerov_ws
source src/bluerov2_control/scripts/source_fixed_hook_real.bash

read -r -p 'Robot profile (glub or splash): ' ROBOT_NAME
if [[ "$ROBOT_NAME" == glub || "$ROBOT_NAME" == splash ]]; then
  BAG_DIR="$PWD/fixed_hook_bags/fixed_hook_${ROBOT_NAME}_$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$PWD/fixed_hook_bags"

  ACK_SUFFIX=$(python3 -c "from px4_msgs.msg import VehicleCommandAck as M; v=int(M.MESSAGE_VERSION); print(f'_v{v}' if v else '')")
  STATUS_SUFFIX=$(python3 -c "from px4_msgs.msg import VehicleStatus as M; v=int(M.MESSAGE_VERSION); print(f'_v{v}' if v else '')")

  ros2 bag record -o "$BAG_DIR" --topics \
    "/mocap/$ROBOT_NAME/pose" \
    "/mocap/$ROBOT_NAME/odom_ekf_fixed_hook" \
    "/mocap/$ROBOT_NAME/vehicle_odometry_fixed_hook" \
    "/$ROBOT_NAME/fmu/in/offboard_control_mode" \
    "/$ROBOT_NAME/fmu/in/vehicle_command" \
    "/$ROBOT_NAME/fmu/in/vehicle_thrust_setpoint" \
    "/$ROBOT_NAME/fmu/in/vehicle_torque_setpoint" \
    "/$ROBOT_NAME/fmu/out/vehicle_command_ack$ACK_SUFFIX" \
    "/$ROBOT_NAME/fmu/out/vehicle_status$STATUS_SUFFIX" \
    "/$ROBOT_NAME/fmu/out/vehicle_control_mode" \
    "/$ROBOT_NAME/fmu/out/vehicle_odometry" \
    "/$ROBOT_NAME/fmu/out/failsafe_flags" \
    /bluerov2/fixed_hook/offboard_request_enable \
    /bluerov2/fixed_hook/mission_enable \
    /bluerov2/fixed_hook/controller_heartbeat \
    /bluerov2/trial_event \
    /rosout \
    /parameter_events
else
  echo 'Select glub or splash; recorder not started.'
fi
```

Leave the bag recorder running through control shutdown. Record external
video with a shared time reference and note its location in the trial
metadata. Mark observed physical outcomes separately from controller state;
a `COMPLETE` event alone does not verify successful hook engagement.

### Analyze a trial

In an offline analysis terminal, select an existing trial directory:

```bash
cd /home/yecheng/bluerov_ws
source src/bluerov2_control/scripts/source_fixed_hook_real.bash

read -r -p 'Trial directory (absolute path): ' TRIAL_DIR
if [[ "$TRIAL_DIR" == /* && -d "$TRIAL_DIR" ]]; then
  ros2 run bluerov2_control analyze_payload_retrieval_trial "$TRIAL_DIR"
else
  echo 'Select an existing absolute trial directory.'
fi
```

Outputs are written to the trial's `analysis/` directory:
`summary_metrics.json`, `summary_metrics.csv`, `thesis_results_summary.md`,
and plots when Matplotlib is available.

### Reproduce the paper figures

With the three original trial directories available, write figures to a
new output directory without replacing the existing publication figures:

```bash
cd /home/yecheng/bluerov_ws
FIGURE_DIR=$(mktemp -d "$PWD/bluerov2_payload_retrieval_trials/paper_figures.XXXXXX")

MPLCONFIGDIR=/tmp/bluerov-paper-mpl python3 \
  src/bluerov2_control/scripts/plot_three_success_trials.py \
  --trials-root "$PWD/bluerov2_payload_retrieval_trials" \
  --output-dir "$FIGURE_DIR"
```
