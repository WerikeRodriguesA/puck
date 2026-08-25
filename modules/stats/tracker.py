"""
modules/stats/tracker.py

Coleta e agrega estatísticas de uso do Puck escutando eventos do EventBus.

Responsabilidade:
    Manter métricas de uso em memória (contagem de palmas, modos ativados,
    falhas de execução, tempo de atividade/uptime) sem acoplamento com
    outros módulos.
"""

from collections import Counter
from datetime import datetime
import threading
from typing import Any, Optional

from core.events import EventBus, EventType, PuckEvent
from utils.logger import get_logger

logger = get_logger(__name__)


class StatsTracker:
    """
    Rastreador de estatísticas do Puck.

    Inscreve-se no EventBus e contabiliza métricas de funcionamento do sistema.
    """

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._start_time: datetime = datetime.now()
        self._total_claps: int = 0
        self._mode_counts: Counter[str] = Counter()
        self._app_launches: int = 0
        self._app_failures: int = 0
        self._total_alerts: int = 0
        self._lock = threading.Lock()

        if event_bus:
            event_bus.subscribe(self.handle_event)

    def handle_event(self, event: PuckEvent) -> None:
        """Handler de eventos registrado no EventBus."""
        with self._lock:
            if event.type == EventType.CLAP_DETECTED:
                if isinstance(event.payload, int):
                    self._total_claps += event.payload
                else:
                    self._total_claps += 1

            elif event.type == EventType.MODE_ACTIVATED:
                mode_name = str(event.payload) if event.payload else "desconhecido"
                self._mode_counts[mode_name] += 1

            elif event.type == EventType.APP_LAUNCHED:
                self._app_launches += 1

            elif event.type == EventType.APP_LAUNCH_FAILED:
                self._app_failures += 1

            elif event.type in (EventType.HIGH_CPU_ALERT, EventType.HIGH_MEMORY_ALERT):
                self._total_alerts += 1

    def get_stats(self) -> dict[str, Any]:
        """
        Retorna relatório consolidado de estatísticas.

        Returns:
            dict com uptime, contagem de palmas, ativações de modo, etc.
        """
        now = datetime.now()
        uptime_seconds = round((now - self._start_time).total_seconds(), 1)

        with self._lock:
            return {
                "start_time": self._start_time.isoformat(),
                "uptime_seconds": uptime_seconds,
                "total_claps_detected": self._total_claps,
                "total_mode_activations": sum(self._mode_counts.values()),
                "mode_activations": dict(self._mode_counts),
                "app_launches": self._app_launches,
                "app_launch_failures": self._app_failures,
                "total_alerts": self._total_alerts,
            }
