"""
tests/test_system_info.py

Testes para modules/monitor/system_info.py

Estratégia de mocking:
    psutil é importado direto no módulo — monkeypatchamos os atributos
    de modules.monitor.system_info.psutil para simular respostas.
"""

from modules.monitor.system_info import PsutilSystemMonitor

import psutil


def _fake_mem():
    class Mem:
        total = 16 * 1024 ** 3
        used = 8 * 1024 ** 3
        available = 8 * 1024 ** 3
        percent = 50.0

    return Mem()


class TestPsutilSystemMonitor:
    def test_get_cpu_usage(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "modules.monitor.system_info.psutil.cpu_percent",
            lambda interval: 42.5,
        )

        monitor = PsutilSystemMonitor()
        assert monitor.get_cpu_usage() == 42.5

    def test_get_memory_usage(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "modules.monitor.system_info.psutil.virtual_memory", _fake_mem
        )

        monitor = PsutilSystemMonitor()
        mem = monitor.get_memory_usage()

        assert mem["total_gb"] == 16.0
        assert mem["used_gb"] == 8.0
        assert mem["percent"] == 50.0

    def test_get_disk_usage(self, monkeypatch) -> None:
        class Disk:
            total = 512 * 1024 ** 3
            used = 256 * 1024 ** 3
            free = 256 * 1024 ** 3
            percent = 50.0

        monkeypatch.setattr(
            "modules.monitor.system_info.psutil.disk_usage",
            lambda path: Disk(),
        )

        monitor = PsutilSystemMonitor()
        disk = monitor.get_disk_usage("C:\\")

        assert disk["total_gb"] == 512.0
        assert disk["used_gb"] == 256.0
        assert disk["free_gb"] == 256.0
        assert disk["percent"] == 50.0

    def test_get_network_info(self, monkeypatch) -> None:
        class Net:
            bytes_sent = 10 * 1024 ** 2
            bytes_recv = 20 * 1024 ** 2

        monkeypatch.setattr(
            "modules.monitor.system_info.psutil.net_io_counters",
            lambda: Net(),
        )

        monitor = PsutilSystemMonitor()
        net = monitor.get_network_info()

        assert net["bytes_sent_mb"] == 10.0
        assert net["bytes_recv_mb"] == 20.0

    def test_get_temperature_returns_none_when_unsupported(
        self, monkeypatch
    ) -> None:
        def raise_attribute_error():
            raise AttributeError()

        monkeypatch.setattr(
            psutil,
            "sensors_temperatures",
            raise_attribute_error,
            raising=False,
        )

        monitor = PsutilSystemMonitor()
        assert monitor.get_temperature() is None

    def test_get_temperature_returns_none_when_attribute_missing(
        self, monkeypatch
    ) -> None:
        # Simula psutil de Windows, onde o atributo nem existe
        if hasattr(psutil, "sensors_temperatures"):
            monkeypatch.delattr(psutil, "sensors_temperatures")

        monitor = PsutilSystemMonitor()
        assert monitor.get_temperature() is None

    def test_get_temperature_returns_none_when_empty(self, monkeypatch) -> None:
        monkeypatch.setattr(
            psutil,
            "sensors_temperatures",
            lambda: {},
            raising=False,
        )

        monitor = PsutilSystemMonitor()
        assert monitor.get_temperature() is None

    def test_get_temperature_returns_value(self, monkeypatch) -> None:
        class Temp:
            current = 55.0

        monkeypatch.setattr(
            psutil,
            "sensors_temperatures",
            lambda: {"coretemp": [Temp()]},
            raising=False,
        )

        monitor = PsutilSystemMonitor()
        assert monitor.get_temperature() == 55.0

    def test_get_full_report_contains_all_sections(self, monkeypatch) -> None:
        class Disk:
            total = 512 * 1024 ** 3
            used = 256 * 1024 ** 3
            free = 256 * 1024 ** 3
            percent = 50.0

        class Net:
            bytes_sent = 10 * 1024 ** 2
            bytes_recv = 20 * 1024 ** 2

        monkeypatch.setattr(
            "modules.monitor.system_info.psutil.cpu_percent",
            lambda interval: 20.0,
        )
        monkeypatch.setattr(
            "modules.monitor.system_info.psutil.cpu_count",
            lambda logical: 8,
        )
        monkeypatch.setattr(
            "modules.monitor.system_info.psutil.virtual_memory", _fake_mem
        )
        monkeypatch.setattr(
            "modules.monitor.system_info.psutil.disk_usage",
            lambda path: Disk(),
        )
        monkeypatch.setattr(
            "modules.monitor.system_info.psutil.net_io_counters",
            lambda: Net(),
        )
        monkeypatch.setattr(
            psutil,
            "sensors_temperatures",
            lambda: {},
            raising=False,
        )

        monitor = PsutilSystemMonitor()
        report = monitor.get_full_report()

        assert set(report.keys()) == {
            "cpu",
            "memory",
            "disk",
            "network",
            "temperature_celsius",
        }
        assert report["cpu"]["usage_percent"] == 20.0
        assert report["cpu"]["cores"] == 8
        assert report["temperature_celsius"] is None

    def test_get_top_processes(self, monkeypatch) -> None:
        class FakeProc:
            def __init__(self, pid, name, memory):
                self.info = {
                    "pid": pid,
                    "name": name,
                    "cpu_percent": 5.0,
                    "memory_percent": memory,
                }

        monkeypatch.setattr(
            "modules.monitor.system_info.psutil.process_iter",
            lambda attrs: [
                FakeProc(100, "chrome.exe", 12.0),
                FakeProc(200, "code.exe", 25.0),
            ],
        )

        monitor = PsutilSystemMonitor()
        procs = monitor.get_top_processes(limit=5)
        assert len(procs) == 2
        assert procs[0]["name"] == "code.exe"  # Ordenado por memória desc
        assert procs[0]["memory_percent"] == 25.0

