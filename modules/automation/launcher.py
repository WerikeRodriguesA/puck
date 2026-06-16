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

    def __init__(self, settings: Settings, mode_manager: ModeManager) -> None:
        """
        Args:
            settings: configurações com caminhos dos apps
            mode_manager: gerenciador de modos para saber quais apps abrir
        """
        self._settings = settings
        self._mode_manager = mode_manager

    def launch(self, app_name: str) -> bool:
        """
        Abre um aplicativo pelo nome da chave no config.yaml.

        Resolve variáveis de ambiente no path (ex: %USERNAME%).
        Verifica se o executável existe antes de tentar abrir.

        Returns:
            True se o processo foi iniciado, False em caso de erro.
        """
        path = self._settings.get_app_path(app_name)

        if not path:
            logger.warning(f"App '{app_name}' não encontrado no config.yaml")
            return False

        # Resolve variáveis de ambiente do Windows (%USERNAME%, %APPDATA%, etc)
        resolved_path = os.path.expandvars(path)

        # Verifica existência — mas só para caminhos absolutos
        # 'wt.exe' (Windows Terminal) está no PATH, não é caminho absoluto
        if os.path.isabs(resolved_path) and not Path(resolved_path).exists():
            logger.error(
                f"Executável não encontrado: {resolved_path}\n"
                f"Verifique o caminho no config.yaml para '{app_name}'"
            )
            return False

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
