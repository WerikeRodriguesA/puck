"""
tests/test_api.py

Testes para api/server.py — usando TestClient com fakes (sem abrir apps reais).
"""

import pytest
from fastapi.testclient import TestClient

from api.server import create_app
from config.settings import Settings
from core.events import EventBus, EventType
from core.modes import ModeManager

REPORT = {
    "cpu": {"usage_percent": 20.0, "cores": 8},
    "memory": {"total_gb": 16.0, "percent": 50.0},
    "disk": {"total_gb": 512.0, "percent": 40.0},
}


class FakeLauncher:
    """Launcher fake — registra chamadas sem abrir nada."""

    def __init__(self) -> None:
        self.launched_modes = []

    def launch(self, app_name: str) -> bool:
        return True

    def launch_mode(self, mode_name: str) -> None:
        self.launched_modes.append(mode_name)


class FakeMonitorService:
    """Monitor fake — devolve o relatório fixo."""

    def __init__(self, report: dict) -> None:
        self.report = report

    def get_latest_report(self) -> dict:
        return self.report

    def get_full_report(self) -> dict:
        return self.report


@pytest.fixture
def api_client(settings: Settings):
    launcher = FakeLauncher()
    mode_manager = ModeManager(settings)
    monitor = FakeMonitorService(REPORT)
    app = create_app(launcher, mode_manager, monitor)
    return TestClient(app), launcher


class TestPuckApi:
    def test_root(self, api_client) -> None:
        client, _ = api_client
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["service"] == "puck"

    def test_health(self, api_client) -> None:
        client, _ = api_client
        assert client.get("/health").json() == {"status": "ok"}

    def test_list_modes(self, api_client) -> None:
        client, _ = api_client
        response = client.get("/modes")
        assert response.status_code == 200
        assert set(response.json()["modes"]) == {"ads", "gamer"}

    def test_get_mode_detail(self, api_client) -> None:
        client, _ = api_client
        response = client.get("/modes/ads")
        assert response.status_code == 200
        assert response.json()["display_name"] == "Modo ADS"
        assert response.json()["apps"] == ["vscode", "spotify"]

    def test_get_mode_not_found(self, api_client) -> None:
        client, _ = api_client
        assert client.get("/modes/nao_existe").status_code == 404

    def test_activate_mode(self, api_client) -> None:
        client, launcher = api_client
        response = client.post("/modes/ads/activate")
        assert response.status_code == 200
        assert response.json() == {"mode": "ads", "activated": True}
        assert launcher.launched_modes == ["ads"]

    def test_activate_mode_not_found(self, api_client) -> None:
        client, launcher = api_client
        assert client.post("/modes/nao_existe/activate").status_code == 404
        assert launcher.launched_modes == []

    def test_activate_mode_publishes_event(self, settings: Settings) -> None:
        bus = EventBus()
        events = []
        bus.subscribe(lambda e: events.append(e), EventType.MODE_ACTIVATED)

        app = create_app(
            launcher=FakeLauncher(),
            mode_manager=ModeManager(settings),
            monitor=FakeMonitorService(REPORT),
            event_bus=bus,
        )
        client = TestClient(app)

        client.post("/modes/gamer/activate")

        assert len(events) == 1
        assert events[0].payload == "gamer"
        assert events[0].source == "api"

    def test_metrics(self, api_client) -> None:
        client, _ = api_client
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.json() == REPORT

    def test_dashboard_returns_html(self, api_client) -> None:
        client, _ = api_client
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Puck Control Center" in response.text

    def test_stats_endpoint(self, settings: Settings) -> None:
        from modules.stats.tracker import StatsTracker
        bus = EventBus()
        stats_tracker = StatsTracker(event_bus=bus)

        app = create_app(
            launcher=FakeLauncher(),
            mode_manager=ModeManager(settings),
            monitor=FakeMonitorService(REPORT),
            event_bus=bus,
            stats_tracker=stats_tracker,
        )
        client = TestClient(app)

        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "uptime_seconds" in data
        assert data["total_claps_detected"] == 0

    def test_deactivate_mode_endpoint(self, api_client) -> None:
        client, _ = api_client
        response = client.post("/modes/ads/deactivate")
        assert response.status_code == 200
        assert response.json() == {"mode": "ads", "deactivated": True}

    def test_stop_app_endpoint(self, api_client) -> None:
        client, _ = api_client
        response = client.post("/apps/vscode/stop")
        assert response.status_code == 200
        assert "stopped" in response.json()

    def test_top_processes_endpoint(self, api_client) -> None:
        client, _ = api_client
        response = client.get("/metrics/processes")
        assert response.status_code == 200
        assert "processes" in response.json()


