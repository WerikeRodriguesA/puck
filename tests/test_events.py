"""
tests/test_events.py

Testes para core/events.py — barramento de eventos (Observer).
"""

import pytest

from core.events import EventBus, EventType, PuckEvent


class TestEventBus:
    def test_type_subscriber_receives_only_its_type(self) -> None:
        bus = EventBus()
        received = []

        bus.subscribe(
            lambda e: received.append(e),
            event_type=EventType.CLAP_DETECTED,
        )

        bus.publish(PuckEvent(EventType.CLAP_DETECTED))
        bus.publish(PuckEvent(EventType.MODE_ACTIVATED))

        assert len(received) == 1
        assert received[0].type == EventType.CLAP_DETECTED

    def test_wildcard_subscriber_receives_all(self) -> None:
        bus = EventBus()
        received = []

        bus.subscribe(lambda e: received.append(e))

        bus.publish(PuckEvent(EventType.CLAP_DETECTED))
        bus.publish(PuckEvent(EventType.APP_LAUNCHED))

        assert [e.type for e in received] == [
            EventType.CLAP_DETECTED,
            EventType.APP_LAUNCHED,
        ]

    def test_multiple_subscribers_same_type(self) -> None:
        bus = EventBus()
        first = []
        second = []

        bus.subscribe(lambda e: first.append(e), EventType.SYSTEM_STARTED)
        bus.subscribe(lambda e: second.append(e), EventType.SYSTEM_STARTED)

        bus.publish(PuckEvent(EventType.SYSTEM_STARTED))

        assert len(first) == 1
        assert len(second) == 1

    def test_publish_preserves_payload_and_source(self) -> None:
        bus = EventBus()
        received = []

        bus.subscribe(lambda e: received.append(e), EventType.APP_LAUNCHED)
        bus.publish(
            PuckEvent(
                EventType.APP_LAUNCHED,
                payload="vscode",
                source="launcher",
            )
        )

        assert received[0].payload == "vscode"
        assert received[0].source == "launcher"

    def test_exception_in_one_handler_does_not_break_others(self) -> None:
        bus = EventBus()
        received = []

        def bad_handler(event: PuckEvent) -> None:
            raise RuntimeError("boom")

        bus.subscribe(bad_handler)
        bus.subscribe(lambda e: received.append(e))

        # Não deve propagar exceção — publicar nunca derruba o fluxo
        bus.publish(PuckEvent(EventType.CLAP_DETECTED))

        assert len(received) == 1

    def test_publish_no_subscribers_does_not_crash(self) -> None:
        bus = EventBus()
        bus.publish(PuckEvent(EventType.CLAP_DETECTED))
