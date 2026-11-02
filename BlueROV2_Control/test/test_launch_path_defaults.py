"""Resolve path arguments without starting ROS nodes or touching hardware."""

import importlib.util
from pathlib import Path

from launch import LaunchContext
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
import pytest

from bluerov2_control.record_mocap_target_pose import parse_args


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
LAUNCHES = (
    ('fixed_hook_pose_validation.launch.py', 'trial_output_dir'),
    ('fixed_hook_mpc_june23.launch.py', 'trial_output_dir'),
    ('payload_retrieval_data_collection.launch.py', 'output_dir'),
)


def _load_launch(filename):
    spec = importlib.util.spec_from_file_location(
        'portable_paths_' + filename.replace('.', '_'),
        PACKAGE_ROOT / 'launch' / filename,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _arguments(module, overrides=None):
    context = LaunchContext()
    context.launch_configurations.update(overrides or {})
    for action in module.generate_launch_description().entities:
        if isinstance(action, DeclareLaunchArgument):
            action.execute(context)
    return context


@pytest.mark.parametrize('filename,output_argument', LAUNCHES)
def test_paths_read_environment_when_launch_is_generated(
    filename, output_argument, monkeypatch, tmp_path,
):
    # Import first: reusing a module must not freeze another user's paths.
    module = _load_launch(filename)
    trial_root = tmp_path / 'trial data'
    solver_root = tmp_path / 'solver source'
    monkeypatch.setenv('TRIALS_DIR', str(trial_root))
    monkeypatch.setenv('ACADOS_SOURCE_DIR', str(solver_root))
    context = _arguments(module)
    assert LaunchConfiguration(output_argument).perform(context) == str(trial_root)
    if output_argument == 'trial_output_dir':
        assert LaunchConfiguration('acados_source_dir').perform(context) == str(solver_root)


@pytest.mark.parametrize('filename,output_argument', LAUNCHES)
def test_explicit_launch_arguments_override_environment(
    filename, output_argument, monkeypatch, tmp_path,
):
    monkeypatch.setenv('TRIALS_DIR', str(tmp_path / 'default trials'))
    monkeypatch.setenv('ACADOS_SOURCE_DIR', str(tmp_path / 'default solver'))
    explicit = {output_argument: str(tmp_path / 'explicit trials')}
    if output_argument == 'trial_output_dir':
        explicit['acados_source_dir'] = str(tmp_path / 'explicit solver')
    context = _arguments(_load_launch(filename), explicit)
    for name, value in explicit.items():
        assert LaunchConfiguration(name).perform(context) == value


@pytest.mark.parametrize('filename,output_argument', LAUNCHES)
def test_empty_trial_variable_uses_configured_workspace(
    filename, output_argument, monkeypatch, tmp_path,
):
    workspace = tmp_path / 'robot workspace'
    monkeypatch.setenv('BLUEROV_WS', str(workspace))
    monkeypatch.setenv('TRIALS_DIR', '')
    context = _arguments(_load_launch(filename))
    assert LaunchConfiguration(output_argument).perform(context) == str(
        workspace / 'bluerov2_payload_retrieval_trials'
    )


def test_recorder_output_defaults_and_explicit_override(monkeypatch, tmp_path):
    workspace = tmp_path / 'robot workspace'
    monkeypatch.setenv('BLUEROV_WS', str(workspace))
    defaults, _ = parse_args([])
    assert defaults.output_file == str(
        workspace / 'target_poses' / 'hooked_box_target_pose_raw.json'
    )
    output = tmp_path / 'measured target.json'
    explicit, _ = parse_args(['--output-file', str(output)])
    assert explicit.output_file == str(output)
    assert explicit.overwrite is False
