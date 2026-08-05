"""
tests/test_monitor_service.py

Testes para modules/monitor/service.py
"""

import time

from core.events import EventBus, EventType
from modules.monitor.service import MonitorService


class FakeMonitor:
    """SystemMonitor fake que entrega relatórios fixos em sequência."""

    def __init__(self, reports: list) -> None:
        self.reports = list(reports)
        self.calls = 0

    def get_cpu_usage(self) -> float:
        return self.reports[0]["cpu"]["usage_percent"]

    def get_memory_usage(self) -> dict:
        return {}

    def get_disk_usage(self, path: str = "/") -> dict:
        return {}

    def get_full_report(self) -> dict:
        report = self.reports[min(self.calls, len(self.reports) - 1)]
        self.calls += 1
        return report


def wait_until(predicate, timeout: float = 3.0, step: float = 0.02) -> bool:
    """Polling simples para testes com threads — evita sleeps cegos."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(step)
    return False


class TestMonitorService:
    def test_start_samples_immediately(self) -> None:
        report = {"cpu": {"usage_percent": 42.0}}
        service = MonitorService(FakeMonitor([report]), interval=60.0)

        service.start()
        try:
            assert service.get_latest_report() == report
        finally:
            service.stop()

    def test_stop_is_idempotent(self) -> None:
        service = MonitorService(FakeMonitor([{}]), interval=0.05)
        service.start()
        service.stop()
        service.stop()  # segunda chamada não deve quebrar

    def test_get_latest_returns_copy(self) -> None:
        report = {"cpu": {"usage_percent": 10.0}}
        service = MonitorService(FakeMonitor([report]))
        service.start()
        try:
            latest = service.get_latest_report()
            latest["cpu"]["usage_percent"] = 999.0
            assert service.get_latest_report() == report
        finally:
            service.stop()

    def test_delegates_live_readings(self) -> None:
        fake = FakeMonitor([{"cpu": {"usage_percent": 55.0}}])
        service = MonitorService(fake)
        assert service.get_cpu_usage() == 55.0

    def test_emits_high_cpu_alert_when_crossing_threshold(self) -> None:
        bus = EventBus()
        alerts = []
        bus.subscribe(lambda e: alerts.append(e), EventType.HIGH_CPU_ALERT)

        reports = [
            {"cpu": {"usage_percent": 30.0}},
            {"cpu": {"usage_percent": 95.0}},
        ]
        service = MonitorService(
            FakeMonitor(reports),
            interval=0.05,
            cpu_alert_threshold=80.0,
            event_bus=bus,
        )

        service.start()
        try:
            assert wait_until(lambda: len(alerts) == 1)
        finally:
            service.stop()

        assert alerts[0].payload == {"cpu": 95.0}

    def test_alert_is_edge_triggered(self) -> None:
        # Sobe, fica alto, desce, sobe de novo → exatamente 2 alertas
        bus = EventBus()
        alerts = []
        bus.subscribe(lambda e: alerts.append(e), EventType.HIGH_CPU_ALERT)

        reports = [
            {"cpu": {"usage_percent": 30.0}},
            {"cpu": {"usage_percent": 95.0}},
            {"cpu": {"usage_percent": 95.0}},
            {"cpu": {"usage_percent": 40.0}},
            {"cpu": {"usage_percent": 95.0}},
        ]
        service = MonitorService(
            FakeMonitor(reports),
            interval=0.05,
            cpu_alert_threshold=80.0,
            event_bus=bus,
        )

        service.start()
        try:
            assert wait_until(lambda: len(alerts) == 2)
        finally:
            service.stop()

        assert len(alerts) == 2

    def test_no_alert_when_threshold_not_configured(self) -> None:
        bus = EventBus()
        alerts = []
        bus.subscribe(lambda e: alerts.append(e))

        service = MonitorService(
            FakeMonitor([{"cpu": {"usage_percent": 99.0}}]),
            interval=0.05,
            event_bus=bus,
        )

        service.start()
        try:
            time.sleep(0.15)
        finally:
            service.stop()

        assert all(a.type != EventType.HIGH_CPU_ALERT for a in alerts)
