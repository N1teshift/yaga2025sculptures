import importlib.util
from pathlib import Path
import asyncio
import types

MODULE_PATH = Path(__file__).resolve().parents[1] / 'server/liquidsoap/mqtt_to_telnet_bridge.py'

spec = importlib.util.spec_from_file_location('mqtt_bridge', MODULE_PATH)
mqtt_bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mqtt_bridge)


class DummyWriter:
    def __init__(self, recorder):
        self.recorder = recorder

    def write(self, data):
        self.recorder.append(data)

    async def drain(self):
        pass

    def close(self):
        self.recorder.append('closed')


async def fake_open_connection(host, port):
    recorder = []
    return None, DummyWriter(recorder), recorder


def test_send_telnet_command(monkeypatch):
    records = []

    async def fake_conn(host, port):
        return None, DummyWriter(records)

    monkeypatch.setattr(mqtt_bridge, 'telnetlib3', types.SimpleNamespace(open_connection=fake_conn))

    async def no_sleep(_):
        pass

    monkeypatch.setattr(mqtt_bridge.asyncio, 'sleep', no_sleep)

    mqtt_bridge.send_telnet_command('A1')

    assert 'set_plan A1\n' in records
    assert 'closed' in records
