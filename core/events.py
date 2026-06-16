"""
core/events.py

Define os eventos que podem ocorrer no sistema Puck.

Por que usar eventos e não chamadas diretas:
    Quando o detector de palmas detecta um evento, ele não deveria saber
    que existe um launcher de apps. Ele só anuncia: "aconteceu algo".
    Quem quiser reagir a esse evento, se registra.

    Isso é o padrão Observer — fundamental para expansão futura.
    Quando comandos de voz existirem, eles vão disparar os mesmos eventos
    que as palmas disparam, sem mudança no resto do sistema.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any


class EventType(Enum):
    """
    Tipos de eventos possíveis no sistema.

    Usar Enum em vez de strings evita typos e facilita autocomplete.
    Novos eventos são adicionados aqui — o resto do sistema não quebra.
    """

    # Eventos do sistema
    SYSTEM_STARTED = auto()
    SYSTEM_STOPPED = auto()

    # Eventos de áudio
    CLAP_DETECTED = auto()         # Uma palma detectada
    DOUBLE_CLAP_DETECTED = auto()  # Duas palmas — ativação principal

    # Eventos de modo
    MODE_ACTIVATED = auto()
    MODE_DEACTIVATED = auto()

    # Eventos de automação
    APP_LAUNCHED = auto()
    APP_LAUNCH_FAILED = auto()

    # Eventos de monitoramento
    HIGH_CPU_ALERT = auto()        # Para alertas futuros
    HIGH_MEMORY_ALERT = auto()

    # Placeholder para eventos futuros
    VOICE_COMMAND_RECEIVED = auto()
    FACE_RECOGNIZED = auto()
    AI_RESPONSE_READY = auto()


@dataclass
class PuckEvent:
    """
    Representa um evento no sistema.

    dataclass gera __init__, __repr__ e __eq__ automaticamente.
    field(default_factory=...) garante que cada evento tenha seu próprio
    timestamp — sem o default_factory, todos compartilhariam o mesmo objeto.
    """

    type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    payload: Any = None  # Dados adicionais opcionais (ex: nome do modo ativado)
    source: str = "system"  # Quem gerou o evento (para logs e debug)

    def __str__(self) -> str:
        return (
            f"[{self.timestamp.strftime('%H:%M:%S')}] "
            f"{self.source} → {self.type.name}"
            + (f" | {self.payload}" if self.payload else "")
        )
