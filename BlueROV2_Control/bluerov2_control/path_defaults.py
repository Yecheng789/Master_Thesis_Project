"""Portable default paths; explicit ROS and command-line options take priority."""

import os
from pathlib import Path


def _environment_path(name: str, default: Path) -> Path:
    """Expand a configured path, treating an empty variable as unset."""
    return Path(os.environ.get(name) or default).expanduser()


def workspace_dir() -> Path:
    """Return the configured ROS workspace or its home-directory default."""
    return _environment_path('BLUEROV_WS', Path.home() / 'bluerov_ws')


def trials_dir() -> Path:
    """Return the default directory for recorded trial data."""
    return _environment_path(
        'TRIALS_DIR', workspace_dir() / 'bluerov2_payload_retrieval_trials',
    )


def acados_dir() -> Path:
    """Return the configured acados source directory."""
    return _environment_path('ACADOS_SOURCE_DIR', Path.home() / 'acados')


def px4_autopilot_dir() -> Path:
    """Return the configured PX4 checkout containing simulation assets."""
    return _environment_path('PX4_AUTOPILOT_DIR', Path.home() / 'PX4-Autopilot')


def target_pose_output_file() -> Path:
    """Keep new target recordings outside source and installation directories."""
    return workspace_dir() / 'target_poses' / 'hooked_box_target_pose_raw.json'
