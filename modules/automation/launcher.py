"""
modules/automation/launcher.py

Implementação concreta do AppLauncher para Windows.

Responsabilidade:
    Abrir executáveis configurados no config.yaml de forma segura.
    Lidar com erros de forma granular — se um app falhar, o modo
    continua tentando abrir os outros.

Por que subprocess e não os.startfile():
    subprocess.Popen dá controle sobre o processo (timeout, erros, etc).
    os.startfile() é mais simples mas não permite capturar falhas de forma
    confiável. Para um sistema que quer crescer, subprocess é a escolha certa.

Implementa: core.interfaces.AppLauncher
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import psutil

from core.events import EventBus, EventType, PuckEvent
from core.interfaces import AppLauncher
from core.modes import ModeManager, WorkMode
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger(__name__)


class WindowsAppLauncher(AppLauncher):
    """
    Launcher de aplicativos para Windows.

    Abre executáveis de forma não-bloqueante (Popen, não run).
    Isso significa: o Puck não espera o app abrir para continuar.
    """

    def __init__(
        self,
        settings: Settings,
        mode_manager: ModeManager,
        event_bus: Optional[EventBus] = None,
        check_running: Optional[bool] = None,
    ) -> None:
        """
        Args:
            settings: configurações com caminhos dos apps
            mode_manager: gerenciador de modos para saber quais apps abrir
            event_bus: barramento de eventos opcional. Se informado,
                       o launcher publica eventos (APP_LAUNCHED, etc).
            check_running: se True, ignora abertura de apps já em execução.
                           Se None, lê de settings ('automation.check_running', False).
        """
        self._settings = settings
        self._mode_manager = mode_manager
        self._event_bus = event_bus

        if check_running is not None:
            self._check_running = check_running
        else:
            auto_cfg = settings.get("automation", {})
            self._check_running = auto_cfg.get("check_running", False)

    def is_app_running(self, app_name: str) -> bool:
        """
        Verifica se o executável do aplicativo já está em execução no sistema.

        Args:
            app_name: chave do aplicativo no config.yaml

        Returns:
            True se o processo estiver rodando, False caso contrário.
        """
        path = self._settings.get_app_path(app_name)
        if not path:
            return False

        resolved_path = os.path.expandvars(path)
        exe_name = Path(resolved_path).name.lower()

        try:
            for proc in psutil.process_iter(["name"]):
                proc_name = proc.info.get("name")
                if proc_name and proc_name.lower() == exe_name:
                    return True
        except Exception as e:
            logger.debug(f"Erro ao checar processos para '{app_name}': {e}")

        return False

    def launch(self, app_name: str, check_running: Optional[bool] = None) -> bool:
        """
        Abre um aplicativo pelo nome da chave no config.yaml.

        Resolve variáveis de ambiente no path (ex: %USERNAME%).
        Verifica se o executável existe antes de tentar abrir.
        Se check_running for True (ou habilitado nas configurações), ignora a abertura caso o app já esteja rodando.

        Returns:
            True se o processo foi iniciado (ou já estava rodando), False em caso de erro.
        """
        should_check = check_running if check_running is not None else self._check_running

        path = self._settings.get_app_path(app_name)

        if not path:
            self._emit_app_launched(app_name, success=False)
            logger.warning(f"App '{app_name}' não encontrado no config.yaml")
            return False

        # Resolve variáveis de ambiente do Windows (%USERNAME%, %APPDATA%, etc)
        resolved_path = os.path.expandvars(path)

        # Verifica existência — mas só para caminhos absolutos
        # 'wt.exe' (Windows Terminal) está no PATH, não é caminho absoluto
        if os.path.isabs(resolved_path) and not Path(resolved_path).exists():
            self._emit_app_launched(app_name, success=False)
            logger.error(
                f"Executável não encontrado: {resolved_path}\n"
                f"Verifique o caminho no config.yaml para '{app_name}'"
            )
            return False

        if should_check and self.is_app_running(app_name):
            logger.info(f"App '{app_name}' já está em execução — abertura ignorada.")
            self._emit_app_launched(app_name, success=True)
            return True

        success = self._open_process(app_name, resolved_path)
        self._emit_app_launched(app_name, success=success)
        return success

    def _open_process(self, app_name: str, resolved_path: str) -> bool:
        """
        Abre o processo de forma não-bloqueante (Popen).

        Returns:
            True se o processo foi iniciado, False em caso de erro.
        """
        try:
            # Popen não bloqueia — o Puck continua rodando normalmente
            # creationflags=DETACHED_PROCESS: o app roda independente do Puck
            subprocess.Popen(
                [resolved_path],
                creationflags=subprocess.DETACHED_PROCESS,
                close_fds=True,
            )
            logger.info(f"App aberto: {app_name} → {resolved_path}")
            return True

        except FileNotFoundError:
            logger.error(f"Executável não encontrado no PATH: {resolved_path}")
            return False

        except PermissionError:
            logger.error(f"Sem permissão para abrir: {resolved_path}")
            return False

        except OSError as e:
            logger.error(f"Erro ao abrir '{app_name}': {e}")
            return False

    def _emit_app_launched(self, app_name: str, success: bool) -> None:
        """Publica evento APP_LAUNCHED ou APP_LAUNCH_FAILED se houver bus."""
        if not self._event_bus:
            return

        event_type = EventType.APP_LAUNCHED if success else EventType.APP_LAUNCH_FAILED
        self._event_bus.publish(
            PuckEvent(event_type, payload=app_name, source="launcher")
        )

    def launch_mode(self, mode_name: str) -> None:
        """
        Ativa um modo e abre todos os seus aplicativos.

        Abre com um pequeno delay entre cada app para não sobrecarregar
        o sistema no momento da inicialização.

        Args:
            mode_name: nome do modo configurado no config.yaml
        """
        mode: WorkMode = self._mode_manager.activate_mode(mode_name)

        if not mode:
            logger.warning(
                f"Modo '{mode_name}' não encontrado. "
                f"Modos disponíveis: {self._mode_manager.list_modes()}"
            )
            return

        if self._event_bus:
            self._event_bus.publish(
                PuckEvent(
                    EventType.MODE_ACTIVATED,
                    payload=mode.name,
                    source="launcher",
                )
            )

        logger.info(f"Ativando: {mode.display_name}")

        success_count = 0
        for app_name in mode.apps:
            if self.launch(app_name):
                success_count += 1
            time.sleep(0.5)  # Delay entre apps — evita pico de uso na inicialização

        logger.info(
            f"{mode.display_name} ativado: "
            f"{success_count}/{len(mode.apps)} apps abertos com sucesso"
        )
