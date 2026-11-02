# Master Thesis Project

Control software, mechanical designs, and experimental assets for a master's
thesis on underwater payload retrieval with BlueROV2.

## Repository structure

```text
Master_Thesis_Project/
├── BlueROV2_Control/   ROS 2 control, planning, experiment guides, and analysis
└── BlueROV2_Hook/      Hook, mounting bracket, and payload-box CAD files
```

### BlueROV2_Control

The ROS 2 package `bluerov2_control` implements fixed-target hook retrieval
for Glub and Splash. It includes A* planning to pre-hook, Fossen-model nonlinear
MPC, MoCap/EKF state estimation, operator confirmation, data logging, and
paper-figure generation.

- [Installation and configuration](BlueROV2_Control/README.md)
- [Glub operator guide](BlueROV2_Control/experiments/payload_retrieval/glub-fixed-hook-guide.md)
- [Splash operator guide](BlueROV2_Control/experiments/payload_retrieval/splash-fixed-hook-guide.md)
- [Data recording and figure reproduction](BlueROV2_Control/experiments/payload_retrieval/README.md)

The documented controller uses recorded target poses and live MoCap feedback.
The separately released YOLO model does not turn this controller into a
camera-only grasping system.

### BlueROV2_Hook

[Mechanical design files](BlueROV2_Hook/) include SolidWorks parts and
assemblies, STL exports, hook arms and links, mounting connections, and the
payload box and handle. Keep the directory structure intact when opening
assemblies. Multiple design editions are included; verify the chosen parts
against the physical installation before fabrication.

## Getting started

For a new ROS workspace, clone the repository under `src`:

```bash
export BLUEROV_WS="${BLUEROV_WS:-$HOME/bluerov_ws}"
mkdir -p "$BLUEROV_WS/src"
git clone https://github.com/Yecheng789/Master_Thesis_Project.git \
  "$BLUEROV_WS/src/Master_Thesis_Project"
```

Follow the [control installation guide](BlueROV2_Control/README.md#installation)
for dependencies, firmware-matched PX4 messages, and build commands. The ROS
package name remains `bluerov2_control`; `colcon` discovers it inside
`BlueROV2_Control/`. Do not keep a second copy of that package in the same
colcon workspace. Existing running installations should be migrated only
with the vehicle stopped and control processes shut down.

## Experimental data and model

The [experimental-assets release](https://github.com/Yecheng789/Master_Thesis_Project/releases/tag/experimental-assets-2026-11-02)
provides downloads separately from the source checkout:

- `Successful-experimental-data.zip`: successful retrieval trial data and plots.
- `handle_v4.pt`: trained YOLO11n handle-detection weights.
- `SHA256SUMS`: checksums for verifying the downloaded assets.

Follow the [reproduction guide](BlueROV2_Control/experiments/payload_retrieval/README.md)
to analyze the recorded trials. The fixed-target results and the detector
weights are separate artifacts, not evidence of a completed visual closed-loop
retrieval experiment.

### Use the handle detector

Download `handle_v4.pt` from the release and install Ultralytics with a
compatible PyTorch build in a separate Python environment. CPU loading and
inference are verified with Ultralytics `8.4.40` and PyTorch `2.14.1+cpu`.
The model contains trained weights and the `handle` class definition; the
original training dataset and the paths recorded in its training metadata
are not required for prediction.

```python
from ultralytics import YOLO

model = YOLO("handle_v4.pt")
results = model.predict(source="image.jpg", device="cpu", save=True)
```

Replace `image.jpg` with an image or video to process. See the
[Ultralytics prediction guide](https://docs.ultralytics.com/modes/predict/)
for supported input types. A working inference call does not establish
detection accuracy or authorize autonomous vehicle operation.

## Safety

Real-vehicle operation requires validated frames, fresh state feedback,
measured operating bounds, and a trained operator with manual takeover and
an emergency stop. Review the robot-specific guide before enabling control.
Offline tests do not replace supervised hardware validation.

## Licensing and provenance

`BlueROV2_Control/` retains the [MIT license](BlueROV2_Control/LICENSE) and
attribution from the control repository, including its upstream BlueROV2 work.
`BlueROV2_Hook/` comes from the [mechanical-design repository](https://github.com/Yecheng789/BlueROV2_Hook)
and has no separate license file; the control package's MIT license is not
extended to the CAD files by this repository layout. Both source histories
are retained in Git.
