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
from typing import Any, Callable, Optional

import threading

from utils.logger import get_logger

logger = get_logger(__name__)


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


Handler = Callable[["PuckEvent"], None]


class EventBus:
    """
    Barramento de eventos — implementa o padrão Observer.

    Como funciona:
        Componentes publicam eventos SEM saber quem escuta (baixo acoplamento).
        Quem quiser reagir a um evento, se registra como subscriber.

        Exemplo:
            launcher.publish(APP_LAUNCHED)  → quem está ouvindo reage.
            Amanhã, um handler de IA ou de dashboard pode se registrar
            sem que o launcher precise mudar UMA linha.

    Thread-safe:
        A detecção de palmas roda em thread separada e publica eventos
        daqui de dentro — por isso o lock.

    Tratamento de erros:
        Um handler que lançar exceção é logado e não derruba os demais.
        Publicar eventos nunca deve quebrar o fluxo principal.
    """

    def __init__(self) -> None:
        # Handlers por tipo de evento
        self._handlers: dict[EventType, list[Handler]] = {}
        # Handlers "curinga" — recebem todos os eventos, qualquer tipo
        self._wildcard_handlers: list[Handler] = []
        self._lock = threading.Lock()

    def subscribe(
        self,
        handler: Handler,
        event_type: Optional[EventType] = None,
    ) -> None:
        """
        Registra um handler.

        Args:
            handler: função chamada a cada evento.
            event_type: se informado, o handler só recebe eventos deste tipo.
                        Se None, recebe todos os eventos (curinga).
        """
        with self._lock:
            if event_type is None:
                self._wildcard_handlers.append(handler)
            else:
                self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: PuckEvent) -> None:
        """
        Notifica todos os subscribers sobre um evento.

        Síncrono por design: os handlers são chamados na thread que publica.
        Para a escala atual isso é o mais simples e previsível.

        Args:
            event: PuckEvent a ser distribuído.
        """
        with self._lock:
            type_handlers = list(self._handlers.get(event.type, []))
            wildcard_handlers = list(self._wildcard_handlers)

        for handler in [*wildcard_handlers, *type_handlers]:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    f"Erro em handler do evento {event.type.name}"
                )


def log_event(event: PuckEvent) -> None:
    """
    Handler padrão: transforma qualquer evento em log estruturado.

    Eventos de falha são logados como ERROR; os demais como INFO.
    Registre este handler uma vez no EventBus e todo o sistema fica auditável.
    """
    level = logger.error if event.type == EventType.APP_LAUNCH_FAILED else logger.info
    level(str(event))
