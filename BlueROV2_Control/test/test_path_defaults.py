"""Verify portable path defaults using only Python's standard library."""

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from bluerov2_control import path_defaults


class PathDefaultsTests(unittest.TestCase):
    """Path resolution is independent of ROS, hardware, and directory creation."""

    def setUp(self):
        self.environ_patch = patch.dict(os.environ)
        self.environ_patch.start()
        self.addCleanup(self.environ_patch.stop)
        for name in (
            'BLUEROV_WS', 'TRIALS_DIR', 'ACADOS_SOURCE_DIR', 'PX4_AUTOPILOT_DIR',
        ):
            os.environ.pop(name, None)
        self.default_home = Path('/tmp/path-defaults-user')
        self.home_patch = patch.object(
            Path, 'home', return_value=self.default_home,
        )
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def _assert_defaults(self):
        workspace = self.default_home / 'bluerov_ws'
        self.assertEqual(path_defaults.workspace_dir(), workspace)
        self.assertEqual(
            path_defaults.trials_dir(),
            workspace / 'bluerov2_payload_retrieval_trials',
        )
        self.assertEqual(
            path_defaults.acados_dir(), self.default_home / 'acados',
        )
        self.assertEqual(
            path_defaults.px4_autopilot_dir(), self.default_home / 'PX4-Autopilot',
        )
        self.assertEqual(
            path_defaults.target_pose_output_file(),
            workspace / 'target_poses' / 'hooked_box_target_pose_raw.json',
        )

    def test_unset_environment_uses_home_defaults(self):
        self._assert_defaults()

    def test_empty_environment_uses_home_defaults(self):
        for name in (
            'BLUEROV_WS', 'TRIALS_DIR', 'ACADOS_SOURCE_DIR', 'PX4_AUTOPILOT_DIR',
        ):
            os.environ[name] = ''
        self._assert_defaults()

    def test_environment_overrides_preserve_spaces(self):
        for name, resolver in (
            ('BLUEROV_WS', path_defaults.workspace_dir),
            ('TRIALS_DIR', path_defaults.trials_dir),
            ('ACADOS_SOURCE_DIR', path_defaults.acados_dir),
            ('PX4_AUTOPILOT_DIR', path_defaults.px4_autopilot_dir),
        ):
            with self.subTest(variable=name):
                configured = '/tmp/custom paths/' + name.lower()
                os.environ[name] = configured
                self.assertEqual(resolver(), Path(configured))

    def test_environment_expands_user_paths(self):
        for name, resolver in (
            ('BLUEROV_WS', path_defaults.workspace_dir),
            ('TRIALS_DIR', path_defaults.trials_dir),
            ('ACADOS_SOURCE_DIR', path_defaults.acados_dir),
            ('PX4_AUTOPILOT_DIR', path_defaults.px4_autopilot_dir),
        ):
            with self.subTest(variable=name):
                configured = '~/custom paths/' + name.lower()
                os.environ[name] = configured
                self.assertEqual(resolver(), Path(configured).expanduser())

    def test_workspace_controls_trial_and_target_defaults(self):
        workspace = Path('/tmp/custom workspace')
        os.environ['BLUEROV_WS'] = str(workspace)
        self.assertEqual(
            path_defaults.trials_dir(),
            workspace / 'bluerov2_payload_retrieval_trials',
        )
        self.assertEqual(
            path_defaults.target_pose_output_file(),
            workspace / 'target_poses' / 'hooked_box_target_pose_raw.json',
        )
        os.environ['TRIALS_DIR'] = '/tmp/separate trial data'
        self.assertEqual(
            path_defaults.trials_dir(), Path('/tmp/separate trial data'),
        )
        self.assertEqual(
            path_defaults.target_pose_output_file(),
            workspace / 'target_poses' / 'hooked_box_target_pose_raw.json',
        )
