"""
main.py — Entry point do Puck

Responsabilidade deste arquivo:
    Inicializar o sistema, conectar os módulos e orquestrar o fluxo principal.

    main.py NÃO implementa lógica de negócio.
    Ele monta as peças, define o que acontece em cada evento, e espera.

    Quando o FastAPI chegar, este arquivo ficará como CLI runner.
    A lógica de inicialização migrará para um Application container.
"""

import signal
import sys
import time

from config.settings import Settings
from core.modes import ModeManager
from modules.audio.detector import ClapDetector
from modules.automation.launcher import WindowsAppLauncher
from modules.monitor.system_info import PsutilSystemMonitor
from utils.logger import configure_logging, get_logger


def main() -> None:
    # ── 1. Carrega configurações ──────────────────────────────────────────────
    settings = Settings()

    # ── 2. Configura logs ────────────────────────────────────────────────────
    log_config = settings.get("logging", {})
    configure_logging(
        level=log_config.get("level", "INFO"),
        log_to_file=log_config.get("log_to_file", True),
        log_dir=settings.logs_dir,
        log_filename=log_config.get("log_filename", "puck.log"),
    )

    logger = get_logger(__name__)
    logger.info("Puck iniciando...")

    # ── 3. Monta os módulos (Dependency Injection manual) ────────────────────
    mode_manager = ModeManager(settings)
    launcher = WindowsAppLauncher(settings, mode_manager)
    monitor = PsutilSystemMonitor()
    detector = ClapDetector(settings)

    # ── 4. Define o que acontece ao detectar dupla palma ────────────────────
    default_mode = settings.get("default_mode", "ads")

    def on_double_clap() -> None:
        """
        Callback disparado pelo ClapDetector.

        Este é o ponto de integração entre áudio e automação.
        O detector não sabe o que isso faz — só chama esta função.
        """
        logger.info("Dupla palma detectada — ativando sistema")

        report = monitor.get_full_report()
        logger.info(
            f"Sistema: CPU {report['cpu']['usage_percent']}% | "
            f"RAM {report['memory']['percent']}% | "
            f"Disco {report['disk']['percent']}%"
        )

        launcher.launch_mode(default_mode)

    # ── 5. Configura encerramento gracioso ────────────────────────────────────
    def shutdown(signum, frame) -> None:
        logger.info("Encerrando Puck...")
        detector.stop()
        logger.info("Puck encerrado.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── 6. Inicia detector e aguarda ─────────────────────────────────────────
    logger.info(
        f"Modos disponíveis: {mode_manager.list_modes()} | "
        f"Modo padrão: {default_mode}"
    )
    logger.info("Aguardando dupla palma para ativar...")

    detector.start(callback=on_double_clap)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
