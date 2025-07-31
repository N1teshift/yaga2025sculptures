#!/usr/bin/env python3
"""Smoke test for the refactored edge agent modules (runs in SIMULATION mode).

Validates the parts that changed without needing real hardware or a broker:
- audio_manager stub returns sane dB levels and accepts volume/mute
- status_collector reads CPU from /proc/stat and a simulated temp
- gpio_utils is a safe no-op under SIMULATION
- paho-mqtt 2.x client constructs (CallbackAPIVersion)
"""
import os
import sys
import importlib.util

os.environ["SIMULATION"] = "1"

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from audio_manager import AudioManager
from status_collector import StatusCollector
from gpio_utils import setup_gpio, SIMULATION
import paho.mqtt.client as mqtt  # ensures 2.x API is importable


def test_audio_manager_stub():
    am = AudioManager(audio_backend="alsa")
    # set_volume/set_mute must not raise and should be no-ops in sim
    am.set_volume(0.5)
    am.set_mute(True)
    mic = am.get_microphone_level()
    out = am.get_output_level()
    assert -60.0 <= mic <= 0.0, f"mic out of range: {mic}"
    assert -60.0 <= out <= 0.0, f"output out of range: {out}"
    print(f"audio_manager stub: mic={mic} out={out} muted={am.is_muted}")


def test_status_collector():
    sc = StatusCollector("1")
    cpu, err = sc.get_cpu_usage()
    assert 0.0 <= cpu <= 100.0, f"cpu out of range: {cpu}"
    temp = sc.get_temperature()
    assert temp > 0, f"temp should be positive in sim: {temp}"
    status = sc.build_status("live", False, -30.0, -25.0)
    assert status["id"] == "1" and status["mode"] == "live"
    print(f"status_collector: cpu={cpu} temp={temp}")


def test_gpio_sim():
    assert SIMULATION is True
    setup_gpio()  # must not raise
    print("gpio_utils: sim no-op OK")


def test_paho_v2():
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    assert c is not None
    print("paho-mqtt 2.x client constructed")


if __name__ == "__main__":
    test_audio_manager_stub()
    test_status_collector()
    test_gpio_sim()
    test_paho_v2()
    print("\nSMOKE TESTS PASSED")
