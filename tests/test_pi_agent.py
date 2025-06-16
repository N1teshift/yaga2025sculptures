import importlib.util
from pathlib import Path
import types

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / 'edge/scripts/pi-agent.py'

spec = importlib.util.spec_from_file_location('pi_agent', MODULE_PATH)
pi_agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pi_agent)


def test_handle_mute_command(monkeypatch):
    agent = pi_agent.SculptureAgent()
    calls = []

    def fake_run(cmd, check=True, **kwargs):
        calls.append(cmd)

    monkeypatch.setattr(pi_agent.subprocess, 'run', fake_run)
    agent.handle_mute_command(True)

    assert calls, 'subprocess.run was not called'
    assert calls[0][0] == 'pactl'
    assert agent.is_muted is True


def test_handle_mode_live(monkeypatch):
    agent = pi_agent.SculptureAgent()
    calls = []

    def fake_run(cmd, check=False, **kwargs):
        calls.append(cmd)

    monkeypatch.setattr(pi_agent.subprocess, 'run', fake_run)
    agent.handle_mode_command('live')

    joined = ' '.join(' '.join(c) for c in calls)
    assert 'darkice.service' in joined
    assert 'player-live.service' in joined
    assert agent.current_mode == 'live'
