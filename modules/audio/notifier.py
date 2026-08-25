"""
modules/audio/notifier.py

Notificador sonoro para confirmação de eventos no Puck (Windows).

Responsabilidade:
    Emitir pequenos sinais sonoros (beeps) ao detectar palmas ou ativar modos,
    fornecendo feedback auditivo imediato ao usuário.
"""

import sys
import threading
from typing import Optional

from core.events import EventBus, EventType, PuckEvent
from utils.logger import get_logger

logger = get_logger(__name__)

# Tenta importar winsound no Windows
try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False


class SoundNotifier:
    """
    Emite beeps de confirmação em resposta a eventos do sistema.
    """

    def __init__(self, enabled: bool = True, event_bus: Optional[EventBus] = None) -> None:
        self._enabled = enabled and WINSOUND_AVAILABLE
        if event_bus and self._enabled:
            event_bus.subscribe(self.handle_event)

    def play_beep(self, frequency: int, duration_ms: int) -> None:
        """Emite um beep em thread separada para não bloquear a thread do EventBus."""
        if not self._enabled:
            return

        def _beep():
            try:
                winsound.Beep(frequency, duration_ms)
            except Exception as e:
                logger.debug(f"Falha ao emitir som: {e}")

        t = threading.Thread(target=_beep, daemon=True, name="sound-notifier")
        t.start()

    def handle_event(self, event: PuckEvent) -> None:
        """Handler do EventBus."""
        if not self._enabled:
            return

        if event.type in (EventType.CLAP_DETECTED, EventType.DOUBLE_CLAP_DETECTED):
            # Beep rápido de detecção (1000Hz, 80ms)
            self.play_beep(1000, 80)
        elif event.type == EventType.MODE_ACTIVATED:
            # Dois beeps ascendentes de ativação
            self.play_beep(800, 60)
            self.play_beep(1200, 100)
