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


def test_cpu_parse_error_included(monkeypatch):
    agent = pi_agent.SculptureAgent()

    def fake_run(cmd, capture_output=True, text=True, check=True, **kwargs):
        if cmd[0] == 'top':
            return types.SimpleNamespace(stdout="Cpu(s): us,\n")
        elif cmd[0] == 'vcgencmd':
            return types.SimpleNamespace(stdout="temp=45.0'C")
        return types.SimpleNamespace(stdout="")

    def fake_check_output(*args, **kwargs):
        return b'0'

    monkeypatch.setattr(pi_agent.subprocess, 'run', fake_run)
    monkeypatch.setattr(pi_agent.subprocess, 'check_output', fake_check_output)

    status = agent.get_system_status()

    assert status['cpu_usage'] == 0
    assert 'error' in status
    assert "Cpu(s): us," in status['error']
