"""Exercise the source helper with fake setup files and no ROS processes."""

import os
from pathlib import Path
import shlex
import subprocess

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/source_fixed_hook_real.bash'
SEARCH_PATHS = (
    'AMENT_PREFIX_PATH', 'CMAKE_PREFIX_PATH', 'COLCON_PREFIX_PATH',
    'PYTHONPATH', 'LD_LIBRARY_PATH',
)


@pytest.fixture
def shell_environment(tmp_path):
    """Inject mock setup and home inputs into an isolated script copy."""
    fake_home = tmp_path / 'user home'
    workspace = fake_home / 'bluerov_ws'
    setup = workspace / 'install/local_setup.bash'
    setup.parent.mkdir(parents=True)
    setup.write_text('return "${MOCK_WORKSPACE_STATUS:-0}"\n')
    ros_setup = tmp_path / 'fake ros setup.bash'
    ros_setup.write_text('''
export ROS_DISTRO=jazzy
ros2() {
  [[ "$*" == 'pkg prefix px4_msgs' ]] || return 99
  printf '%s\\n' "$MOCK_PREFIX"
  return "${MOCK_PREFIX_STATUS:-0}"
}
python3() {
  [[ "$1" == '-c' && "$2" == *'VehicleCommandAck'* ]] || return 99
  printf '%s\\n' "${MOCK_VERSIONS:-0 1}"
  return "${MOCK_VERSION_STATUS:-0}"
}
return "${MOCK_ROS_STATUS:-0}"
''')
    isolated_script = tmp_path / 'source helper with spaces.bash'
    source = SCRIPT.read_text()
    assert source.count('/opt/ros/jazzy/setup.bash') == 1
    assert '${BLUEROV_WS:-${HOME}/bluerov_ws}' in source
    assert '${PX4_WS:-${HOME}/px4_ws}' in source
    assert '${ACADOS_SOURCE_DIR:-${HOME}/acados}' in source
    isolated_script.write_text(
        source.replace('/opt/ros/jazzy/setup.bash', shlex.quote(str(ros_setup)))
        .replace('${HOME}', '${FIXED_HOOK_TEST_HOME}')
    )
    env = os.environ.copy()
    for name in (*SEARCH_PATHS, 'BLUEROV_WS', 'PX4_WS', 'ACADOS_SOURCE_DIR',
                 'ROS_DOMAIN_ID', 'ROS_DISTRO', 'RMW_IMPLEMENTATION'):
        env.pop(name, None)
    # Only the script copy receives a mock home input. HOME and the real ROS
    # setup remain untouched, including in the child process environment.
    env.update(FIXED_HOOK_TEST_HOME=str(fake_home),
               MOCK_PREFIX=str(workspace / 'install/px4_msgs'))
    return isolated_script, env, fake_home, workspace, ros_setup


def run_source(script, env):
    result = subprocess.run(
        ['bash', '--noprofile', '--norc', '-c', '''
source "$1"
status=$?
for name in BLUEROV_WS ACADOS_SOURCE_DIR RMW_IMPLEMENTATION ROS_DOMAIN_ID \\
  AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH PYTHONPATH LD_LIBRARY_PATH
do
  printf 'TEST:%s=%s\\n' "$name" "${!name-<unset>}"
done
if declare -F _fixed_hook_source_environment >/dev/null; then
  printf 'TEST:helper_leaked=true\\n'
fi
exit "$status"
''', 'test-source-helper', str(script)],
        env=env, capture_output=True, text=True, check=False,
    )
    values = dict(line.removeprefix('TEST:').split('=', 1)
                  for line in result.stdout.splitlines() if line.startswith('TEST:'))
    return result, values


@pytest.mark.parametrize('empty_overrides', [False, True])
def test_defaults_and_empty_environment_use_mock_home(shell_environment, empty_overrides):
    script, env, fake_home, workspace, _ = shell_environment
    if empty_overrides:
        env.update(BLUEROV_WS='', PX4_WS='', ACADOS_SOURCE_DIR='')
    old_prefix = fake_home / 'px4_ws/install/px4_msgs'
    env['AMENT_PREFIX_PATH'] = f'{old_prefix}:{old_prefix}/lib:/keep'
    result, values = run_source(script, env)
    assert result.returncode == 0, result.stderr
    assert values['BLUEROV_WS'] == str(workspace)
    assert values['ACADOS_SOURCE_DIR'] == str(fake_home / 'acados')
    assert values['AMENT_PREFIX_PATH'] == '/keep'
    assert values['LD_LIBRARY_PATH'] == str(fake_home / 'acados/lib')
    assert values['RMW_IMPLEMENTATION'] == 'rmw_fastrtps_cpp'
    assert values['ROS_DOMAIN_ID'] == '<unset>'
    assert 'helper_leaked' not in values


def test_overrides_spaces_and_exact_prefix_cleanup(shell_environment):
    script, env, fake_home, _, _ = shell_environment
    workspace = fake_home / 'custom workspace [A]'
    old_workspace = fake_home / 'old workspace [B]'
    acados = fake_home / 'custom acados'
    setup = workspace / 'install/local_setup.bash'
    setup.parent.mkdir(parents=True)
    setup.write_text('return 0\n')
    prefix = workspace / 'install/px4_msgs'
    old_prefix = old_workspace / 'install/px4_msgs'
    env.update(BLUEROV_WS=f'{workspace}/', PX4_WS=f'{old_workspace}/',
               ACADOS_SOURCE_DIR=str(acados), MOCK_PREFIX=str(prefix), ROS_DOMAIN_ID='47')
    retained = [str(prefix) + '-sibling', str(old_prefix) + '_backup/lib',
                '/unrelated path/[literal]*', '/another']
    initial = ':'.join([str(prefix), retained[0], str(prefix / 'lib'),
                        str(old_prefix), retained[1], str(old_prefix / 'lib'),
                        retained[2], retained[3]])
    env.update({name: initial for name in SEARCH_PATHS})
    result, values = run_source(script, env)
    assert result.returncode == 0, result.stderr
    for name in SEARCH_PATHS:
        expected = ':'.join(retained)
        if name == 'LD_LIBRARY_PATH':
            expected = f'{acados}/lib:{expected}'
        assert values[name] == expected
    assert values['BLUEROV_WS'] == str(workspace)
    assert values['ACADOS_SOURCE_DIR'] == str(acados)
    assert values['ROS_DOMAIN_ID'] == '47'
    assert 'helper_leaked' not in values


@pytest.mark.parametrize(('overrides', 'message'), [
    ({'MOCK_PREFIX': '/wrong/install/px4_msgs'}, 'wrong px4_msgs overlay'),
    ({'MOCK_PREFIX_STATUS': '1'}, 'cannot resolve the active px4_msgs'),
    ({'MOCK_VERSIONS': '1 4'}, 'versions do not match'),
    ({'MOCK_VERSION_STATUS': '1'}, 'cannot inspect px4_msgs'),
    ({'MOCK_ROS_STATUS': '1'}, 'ROS setup failed'),
    ({'MOCK_WORKSPACE_STATUS': '1'}, 'workspace setup failed'),
])
def test_safety_failures_return_nonzero(shell_environment, overrides, message):
    script, env, _, _, _ = shell_environment
    env.update(overrides, ROS_DOMAIN_ID='59')
    result, values = run_source(script, env)
    assert result.returncode == 1
    assert message in result.stderr
    assert 'environment ready' not in result.stdout
    assert values['ROS_DOMAIN_ID'] == '59'
    assert 'helper_leaked' not in values


def test_missing_workspace_is_rejected(shell_environment):
    script, env, fake_home, _, _ = shell_environment
    env['BLUEROV_WS'] = str(fake_home / 'not built')
    result, _ = run_source(script, env)
    assert result.returncode == 1
    assert 'required setup file is missing' in result.stderr
    assert 'environment ready' not in result.stdout


def test_executing_instead_of_sourcing_reports_actual_script_path(shell_environment):
    script, env, _, _, _ = shell_environment
    result = subprocess.run(['bash', str(script)], env=env, capture_output=True,
                            text=True, check=False)
    assert result.returncode == 2
    assert 'source this script' in result.stderr
    suggested_command = result.stderr.splitlines()[-1]
    assert shlex.split(suggested_command) == ['source', str(script)]
