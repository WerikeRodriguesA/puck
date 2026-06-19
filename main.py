"""
main.py — Entry point do Puck

Responsabilidade deste arquivo:
    Inicializar o sistema, conectar os módulos e orquestrar o fluxo principal.

    main.py NÃO implementa lógica de negócio.
    Ele monta as peças, define o que acontece em cada evento, e espera.
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

    # ── 3. Monta os módulos ───────────────────────────────────────────────────
    mode_manager = ModeManager(settings)
    launcher = WindowsAppLauncher(settings, mode_manager)
    monitor = PsutilSystemMonitor()
    detector = ClapDetector(settings)

    # ── 4. Lê o mapeamento de palmas → modos do config.yaml ──────────────────
    #
    # Estrutura esperada no config.yaml:
    #   clap_modes:
    #     2: ads
    #     3: estudo
    #     4: gamer
    #
    # YAML carrega chaves numéricas como int — fazemos a conversão explícita
    # para garantir que a busca por chave funcione independente do tipo.
    raw_clap_modes = settings.get("clap_modes", {})
    clap_modes: dict[int, str] = {int(k): str(v) for k, v in raw_clap_modes.items()}

    # Fallback: se clap_modes não estiver configurado, usa o default_mode para 2 palmas
    if not clap_modes:
        default_mode = settings.get("default_mode", "ads")
        clap_modes = {2: default_mode}
        logger.warning(
            f"'clap_modes' não encontrado no config.yaml. "
            f"Usando fallback: 2 palmas → {default_mode}"
        )

    logger.info(
        f"Modos disponíveis: {mode_manager.list_modes()} | "
        f"Mapeamento: { {k: v for k, v in clap_modes.items()} }"
    )

    # ── 5. Define o callback de detecção ─────────────────────────────────────
    def on_clap_sequence(clap_count: int) -> None:
        """
        Chamado pelo ClapDetector ao final de cada sequência de palmas.

        Recebe a contagem e decide qual modo ativar consultando clap_modes.
        Se a contagem não estiver mapeada, loga aviso e não faz nada.

        Separação de responsabilidades:
            - ClapDetector: conta palmas e entrega o número
            - on_clap_sequence: traduz número → nome do modo
            - launcher.launch_mode: executa o modo
        """
        logger.info(f"Sequência recebida: {clap_count} palma(s)")

        mode_name = clap_modes.get(clap_count)

        if not mode_name:
            modos_disponiveis = sorted(clap_modes.keys())
            logger.warning(
                f"{clap_count} palma(s) não mapeada(s). "
                f"Contagens configuradas: {modos_disponiveis}"
            )
            return

        # Log de status do sistema antes de ativar
        report = monitor.get_full_report()
        logger.info(
            f"Sistema: CPU {report['cpu']['usage_percent']}% | "
            f"RAM {report['memory']['percent']}% | "
            f"Disco {report['disk']['percent']}%"
        )

        logger.info(f"{clap_count} palma(s) → ativando modo '{mode_name}'")
        launcher.launch_mode(mode_name)

    # ── 6. Configura encerramento gracioso ────────────────────────────────────
    def shutdown(signum, frame) -> None:
        logger.info("Encerrando Puck...")
        detector.stop()
        logger.info("Puck encerrado.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── 7. Inicia e aguarda ───────────────────────────────────────────────────
    logger.info("Aguardando sequência de palmas...")
    detector.start(callback=on_clap_sequence)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()