"""
modules/monitor/service.py

Coleta métricas do sistema em loop, em thread separada.

Por que um serviço e não só o PsutilSystemMonitor:
    Chamar psutil a cada request da API seria caro e bloqueante
    (get_full_report faz cpu_percent(interval=1), que espera 1s).
    Este serviço amostra em intervalos fixos, guarda o último relatório
    e expõe get_latest_report() para leituras instantâneas.

Além de amostrar, monitora limiares e publica eventos de alerta
(HIGH_CPU_ALERT / HIGH_MEMORY_ALERT) quando a métrica cruza o limite.
Disparo é edge-triggered: alerta só é publicado ao SUBIR acima do limite,
e só volta a disparar depois de cair abaixo dele.

Implementa: core.interfaces.SystemMonitor (por delegação)
"""

import threading
import time
from typing import Optional

from core.events import EventBus, EventType, PuckEvent
from core.interfaces import SystemMonitor
from utils.logger import get_logger

logger = get_logger(__name__)


class MonitorService(SystemMonitor):
    """
    Wrapper do SystemMonitor que amostra em loop e mantém o último relatório.

    Uso:
        service = MonitorService(monitor, interval=2.0, event_bus=bus)
        service.start()
        report = service.get_latest_report()  # instantâneo
        service.stop()
    """

    def __init__(
        self,
        monitor: SystemMonitor,
        interval: float = 2.0,
        cpu_alert_threshold: Optional[float] = None,
        memory_alert_threshold: Optional[float] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        """
        Args:
            monitor: implementação concreta de SystemMonitor (ex: psutil).
            interval: segundos entre cada amostra.
            cpu_alert_threshold: % de CPU que dispara HIGH_CPU_ALERT (None = desliga).
            memory_alert_threshold: % de RAM que dispara HIGH_MEMORY_ALERT.
            event_bus: barramento opcional para publicar alertas.
        """
        self._monitor = monitor
        self._interval = interval
        self._cpu_alert_threshold = cpu_alert_threshold
        self._memory_alert_threshold = memory_alert_threshold
        self._event_bus = event_bus

        self._latest: dict = {}
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Estado dos alertas — evita re-disparar enquanto o valor segue alto
        self._active_alerts: dict[EventType, bool] = {
            EventType.HIGH_CPU_ALERT: False,
            EventType.HIGH_MEMORY_ALERT: False,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Contrato SystemMonitor — delega para leituras ao vivo
    # ──────────────────────────────────────────────────────────────────────────

    def get_cpu_usage(self) -> float:
        return self._monitor.get_cpu_usage()

    def get_memory_usage(self) -> dict:
        return self._monitor.get_memory_usage()

    def get_disk_usage(self, path: str = "/") -> dict:
        return self._monitor.get_disk_usage(path)

    def get_full_report(self) -> dict:
        return self._monitor.get_full_report()

    # ──────────────────────────────────────────────────────────────────────────
    # API do serviço
    # ──────────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """
        Inicia o loop de amostragem em thread dedicada.

        A primeira amostra é feita de forma síncrona para que
        get_latest_report() tenha dados imediatamente após o start().
        """
        if self._running:
            logger.warning("MonitorService já está rodando")
            return

        self._running = True
        self._sample_once()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="monitor-loop",
        )
        self._thread.start()

        logger.info(f"MonitorService iniciado (intervalo={self._interval}s)")

    def stop(self) -> None:
        """Para o loop e libera a thread."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

        logger.info("MonitorService parado")

    def get_latest_report(self) -> dict:
        """
        Retorna o último relatório amostrado, de forma instantânea.

        Returns:
            Cópia do relatório. Se nada foi amostrado ainda, dict vazio.
        """
        with self._lock:
            return dict(self._latest)

    # ──────────────────────────────────────────────────────────────────────────
    # Loop interno
    # ──────────────────────────────────────────────────────────────────────────

    def _sample_once(self) -> None:
        """Coleta um relatório e verifica alertas. Erros são logados, não derrubam o loop."""
        try:
            report = self._monitor.get_full_report()
            with self._lock:
                self._latest = report
            self._check_alerts(report)
        except Exception as e:
            logger.error(f"Erro ao amostrar sistema: {e}", exc_info=True)

    def _loop(self) -> None:
        while self._running and not self._stop_event.is_set():
            self._sample_once()
            self._stop_event.wait(self._interval)

    def _check_alerts(self, report: dict) -> None:
        """Publica alertas edge-triggered com base nos limiares configurados."""
        if not self._event_bus:
            return

        cpu = report.get("cpu", {}).get("usage_percent")
        if cpu is not None:
            self._check_threshold(
                label="CPU",
                value=cpu,
                threshold=self._cpu_alert_threshold,
                event_type=EventType.HIGH_CPU_ALERT,
            )

        memory = report.get("memory", {}).get("percent")
        if memory is not None:
            self._check_threshold(
                label="Memória",
                value=memory,
                threshold=self._memory_alert_threshold,
                event_type=EventType.HIGH_MEMORY_ALERT,
            )

    def _check_threshold(
        self,
        label: str,
        value: float,
        threshold: Optional[float],
        event_type: EventType,
    ) -> None:
        if threshold is None:
            return

        if value >= threshold and not self._active_alerts[event_type]:
            self._active_alerts[event_type] = True
            logger.warning(f"{label} alto: {value}% (limite {threshold}%)")
            self._event_bus.publish(
                PuckEvent(event_type, payload={label.lower(): value}, source="monitor")
            )
        elif value < threshold and self._active_alerts[event_type]:
            self._active_alerts[event_type] = False
