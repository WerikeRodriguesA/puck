"""
api/server.py

API REST do Puck (FastAPI).

Responsabilidade:
    Expor controle e métricas do sistema via HTTP.

Arquitetura (Dependency Injection):
    create_app() recebe as dependências prontas — não constrói nada.
    Isso permite:
        - testar a API com fakes (sem abrir apps reais)
        - substituir componentes sem tocar na API
        - usar a mesma instância do app em main.py e nos testes

Endpoints:
    GET  /                          → identificação do serviço
    GET  /health                    → healthcheck
    GET  /modes                     → lista de modos disponíveis
    GET  /modes/{mode_name}         → detalhe de um modo
    POST /modes/{mode_name}/activate → ativa um modo (abre os apps)
    GET  /metrics                   → último relatório do sistema (cache)
"""

from typing import Optional

from fastapi import FastAPI, HTTPException

from core.events import EventBus, EventType, PuckEvent
from core.interfaces import AppLauncher, SystemMonitor
from core.modes import ModeManager
from modules.monitor.service import MonitorService


def create_app(
    launcher: AppLauncher,
    mode_manager: ModeManager,
    monitor: MonitorService,
    event_bus: Optional[EventBus] = None,
) -> FastAPI:
    """
    Monta a aplicação FastAPI com as dependências injetadas.

    Args:
        launcher: abre aplicativos e modos.
        mode_manager: consulta modos configurados.
        monitor: fornece o último relatório do sistema (cache).
        event_bus: opcional — usado para publicar eventos de ativação.
    """
    app = FastAPI(title="Puck API", version="0.1.0")

    @app.get("/")
    def root() -> dict:
        return {"service": "puck", "status": "running"}

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/modes")
    def list_modes() -> dict:
        return {"modes": mode_manager.list_modes()}

    @app.get("/modes/{mode_name}")
    def get_mode(mode_name: str) -> dict:
        mode = mode_manager.get_mode(mode_name)
        if not mode:
            raise HTTPException(
                status_code=404,
                detail=f"Modo '{mode_name}' não encontrado",
            )
        return {
            "name": mode.name,
            "display_name": mode.display_name,
            "apps": mode.apps,
        }

    @app.post("/modes/{mode_name}/activate")
    def activate_mode(mode_name: str) -> dict:
        mode = mode_manager.get_mode(mode_name)
        if not mode:
            raise HTTPException(
                status_code=404,
                detail=f"Modo '{mode_name}' não encontrado",
            )

        if event_bus:
            event_bus.publish(
                PuckEvent(
                    EventType.MODE_ACTIVATED,
                    payload=mode_name,
                    source="api",
                )
            )

        launcher.launch_mode(mode_name)
        return {"mode": mode_name, "activated": True}

    @app.get("/metrics")
    def metrics() -> dict:
        report = monitor.get_latest_report()
        if not report:
            # Sem amostra ainda — coleta uma ao vivo em vez de responder vazio
            report = monitor.get_full_report()
        return report

    return app
