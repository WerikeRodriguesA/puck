"""
tests/test_stats.py

Testes para modules/stats/tracker.py
"""

from core.events import EventBus, EventType, PuckEvent
from modules.stats.tracker import StatsTracker


class TestStatsTracker:
    def test_initial_stats(self) -> None:
        tracker = StatsTracker()
        stats = tracker.get_stats()

        assert stats["total_claps_detected"] == 0
        assert stats["total_mode_activations"] == 0
        assert stats["mode_activations"] == {}
        assert stats["app_launches"] == 0
        assert stats["app_launch_failures"] == 0
        assert stats["uptime_seconds"] >= 0

    def test_tracks_clap_events(self) -> None:
        bus = EventBus()
        tracker = StatsTracker(event_bus=bus)

        bus.publish(PuckEvent(EventType.CLAP_DETECTED, payload=2, source="audio"))
        bus.publish(PuckEvent(EventType.CLAP_DETECTED, payload=3, source="audio"))

        stats = tracker.get_stats()
        assert stats["total_claps_detected"] == 5

    def test_tracks_mode_activations(self) -> None:
        bus = EventBus()
        tracker = StatsTracker(event_bus=bus)

        bus.publish(PuckEvent(EventType.MODE_ACTIVATED, payload="ads", source="launcher"))
        bus.publish(PuckEvent(EventType.MODE_ACTIVATED, payload="ads", source="launcher"))
        bus.publish(PuckEvent(EventType.MODE_ACTIVATED, payload="gamer", source="launcher"))

        stats = tracker.get_stats()
        assert stats["total_mode_activations"] == 3
        assert stats["mode_activations"] == {"ads": 2, "gamer": 1}

    def test_tracks_app_launches_and_failures(self) -> None:
        bus = EventBus()
        tracker = StatsTracker(event_bus=bus)

        bus.publish(PuckEvent(EventType.APP_LAUNCHED, payload="vscode", source="launcher"))
        bus.publish(PuckEvent(EventType.APP_LAUNCH_FAILED, payload="unknown", source="launcher"))

        stats = tracker.get_stats()
        assert stats["app_launches"] == 1
        assert stats["app_launch_failures"] == 1
