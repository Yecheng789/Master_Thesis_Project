"""Check analysis paths without importing ROS or optional plotting packages."""

import argparse
import ast
import os
from pathlib import Path

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PATH_SOURCES = (
    'scripts/plot_three_success_trials.py',
    'test/test_restored_fixed_target_baseline.py',
)


def _load_path_functions(relative_path):
    """Load only the dependency-free path and argument functions under test."""
    source_path = PACKAGE_ROOT / relative_path
    tree = ast.parse(source_path.read_text(encoding='utf-8'))
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {'_default_trials_root', 'parse_args'}
    ]
    namespace = {
        'argparse': argparse,
        'os': os,
        'Path': Path,
        '__file__': str(source_path),
    }
    module = ast.Module(body=functions, type_ignores=[])
    exec(compile(module, str(source_path), 'exec'), namespace)
    return namespace


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    monkeypatch.delenv('BLUEROV_WS', raising=False)
    monkeypatch.delenv('TRIALS_DIR', raising=False)


@pytest.mark.parametrize('source', PATH_SOURCES)
@pytest.mark.parametrize('layout', (
    'src/bluerov2_control',
    'src/Master_Thesis_Project/BlueROV2_Control',
))
def test_infers_both_source_layouts(source, layout, tmp_path):
    resolve = _load_path_functions(source)['_default_trials_root']
    assert resolve(tmp_path / layout) == (
        tmp_path / 'bluerov2_payload_retrieval_trials'
    )


@pytest.mark.parametrize('source', PATH_SOURCES)
def test_explicit_workspace_overrides_source_location(
    source, tmp_path, monkeypatch,
):
    monkeypatch.setenv('BLUEROV_WS', str(tmp_path / 'explicit'))
    resolve = _load_path_functions(source)['_default_trials_root']
    assert resolve(tmp_path / 'src' / 'bluerov2_control') == (
        tmp_path / 'explicit' / 'bluerov2_payload_retrieval_trials'
    )


@pytest.mark.parametrize('source', PATH_SOURCES)
def test_trials_directory_takes_precedence_and_expands_user(
    source, tmp_path, monkeypatch,
):
    monkeypatch.setenv('BLUEROV_WS', str(tmp_path / 'workspace'))
    monkeypatch.setenv('TRIALS_DIR', '~/recorded_trials')
    resolve = _load_path_functions(source)['_default_trials_root']
    assert resolve(tmp_path / 'src' / 'bluerov2_control') == (
        Path.home() / 'recorded_trials'
    )


@pytest.mark.parametrize('source', PATH_SOURCES)
def test_standalone_clone_uses_default_workspace(source, tmp_path, monkeypatch):
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
    resolve = _load_path_functions(source)['_default_trials_root']
    assert resolve(tmp_path / 'checkout' / 'BlueROV2_Control') == (
        tmp_path / 'bluerov_ws' / 'bluerov2_payload_retrieval_trials'
    )


def test_plot_cli_paths_override_environment(tmp_path, monkeypatch):
    monkeypatch.setenv('TRIALS_DIR', str(tmp_path / 'environment'))
    parse_args = _load_path_functions(PATH_SOURCES[0])['parse_args']
    trials_root = tmp_path / 'cli_trials'
    args = parse_args(['--trials-root', str(trials_root)])
    assert args.trials_root == trials_root
    assert args.output_dir == trials_root / 'paper_figures_three_success'
    output_dir = tmp_path / 'cli_figures'
    args = parse_args([
        '--trials-root', str(trials_root), '--output-dir', str(output_dir),
    ])
    assert args.output_dir == output_dir


def test_plot_defaults_use_explicit_trials_directory(tmp_path, monkeypatch):
    monkeypatch.setenv('TRIALS_DIR', str(tmp_path / 'recorded_trials'))
    parse_args = _load_path_functions(PATH_SOURCES[0])['parse_args']
    args = parse_args([])
    assert args.trials_root == tmp_path / 'recorded_trials'
    assert args.output_dir == args.trials_root / 'paper_figures_three_success'
