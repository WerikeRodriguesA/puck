"""
main.py — Entry point do Puck

Responsabilidade deste arquivo:
    Inicializar o sistema, conectar os módulos e orquestrar o fluxo principal.

    main.py NÃO implementa lógica de negócio.
    Ele monta as peças, define o que acontece em cada evento, e espera.

Linha de comando suportada:
    python main.py                      → escuta palmas (padrão)
    python main.py --mode ads           → ativa o modo 'ads' ao iniciar
    python main.py --no-audio           → não escuta palmas (sem microfone)
    python main.py --config outro.yaml  → usa outro arquivo de configuração
    python main.py --list-modes         → lista modos e encerra
"""

import argparse
import signal
import sys
import threading
import time
from pathlib import Path

from config.settings import Settings
from core.events import EventBus, EventType, PuckEvent, log_event
from core.modes import ModeManager
from modules.audio.detector import ClapDetector
from modules.audio.notifier import SoundNotifier
from modules.automation.launcher import WindowsAppLauncher
from modules.monitor.service import MonitorService
from modules.monitor.system_info import PsutilSystemMonitor
from modules.stats.tracker import StatsTracker
from utils.logger import configure_logging, get_logger


def parse_args(argv=None) -> argparse.Namespace:
    """
    Interpreta os argumentos de linha de comando.

    Separado de main() para ser testável de forma isolada.
    """
    parser = argparse.ArgumentParser(
        prog="puck",
        description="Puck — Personal Utility Control Kernel",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Caminho alternativo para o config.yaml",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default=None,
        help="Ativa um modo imediatamente ao iniciar (ex: --mode ads)",
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Não inicia a escuta de palmas (útil sem microfone)",
    )
    parser.add_argument(
        "--list-modes",
        action="store_true",
        help="Lista os modos disponíveis e encerra",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()

    # ── 1. Carrega configurações ──────────────────────────────────────────────
    if args.config:
        settings = Settings(config_path=Path(args.config))
    else:
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

    # Valida configurações
    validation_errors = settings.validate()
    if validation_errors:
        for err in validation_errors:
            logger.warning(f"Inconsistência na configuração: {err}")

    # ── 3. Barramento de eventos ─────────────────────────────────────────────
    # Qualquer componente publica eventos; quem quiser reagir se registra.
    # log_event é o handler padrão: transforma tudo em log estruturado.
    event_bus = EventBus()
    event_bus.subscribe(log_event)

    # ── 4. Monta os módulos ──────────────────────────────────────────────────
    mode_manager = ModeManager(settings)
    launcher = WindowsAppLauncher(settings, mode_manager, event_bus=event_bus)
    monitor = PsutilSystemMonitor()
    stats_tracker = StatsTracker(event_bus=event_bus)

    audio_cfg = settings.audio_config
    sound_notifier = SoundNotifier(
        enabled=audio_cfg.get("sound_feedback", True),
        event_bus=event_bus,
    )

    # Serviço de monitoramento contínuo — amostra em thread separada
    monitor_cfg = settings.get("monitor", {})
    monitor_service = MonitorService(
        monitor,
        interval=monitor_cfg.get("interval_seconds", 2.0),
        cpu_alert_threshold=monitor_cfg.get("cpu_alert_threshold"),
        memory_alert_threshold=monitor_cfg.get("memory_alert_threshold"),
        event_bus=event_bus,
    )

    detector = ClapDetector(settings)

    # ── 5. Modo utilitário: listar modos ─────────────────────────────────────
    if args.list_modes:
        print("Modos disponíveis:")
        for name in mode_manager.list_modes():
            print(f"  - {name}")
        return

    # ── 6. Lê o mapeamento de palmas → modos do config.yaml ──────────────────
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

    # ── 7. Define o callback de detecção ─────────────────────────────────────
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
        # Publica o evento de áudio — qualquer subscriber pode reagir
        event_bus.publish(
            PuckEvent(EventType.CLAP_DETECTED, payload=clap_count, source="audio")
        )
        if clap_count == 2:
            event_bus.publish(
                PuckEvent(
                    EventType.DOUBLE_CLAP_DETECTED,
                    payload=clap_count,
                    source="audio",
                )
            )

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

    # ── 8. Configura encerramento gracioso ───────────────────────────────────
    def shutdown(signum, frame) -> None:
        logger.info("Encerrando Puck...")
        detector.stop()
        monitor_service.stop()
        event_bus.publish(PuckEvent(EventType.SYSTEM_STOPPED, source="main"))
        logger.info("Puck encerrado.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── 9. Inicia monitoramento contínuo ─────────────────────────────────────
    monitor_service.start()

    # ── 10. API REST (opcional) ──────────────────────────────────────────────
    # Import lazy: se fastapi/uvicorn não estiverem instalados,
    # o resto do Puck continua funcionando normalmente.
    api_cfg = settings.get("api", {})
    if api_cfg.get("enabled", False):
        from api.server import create_app
        import uvicorn

        app = create_app(
            launcher=launcher,
            mode_manager=mode_manager,
            monitor=monitor_service,
            event_bus=event_bus,
            stats_tracker=stats_tracker,
        )
        host = api_cfg.get("host", "0.0.0.0")
        port = int(api_cfg.get("port", 8000))

        api_thread = threading.Thread(
            target=uvicorn.run,
            args=(app,),
            kwargs={"host": host, "port": port},
            daemon=True,
            name="api-server",
        )
        api_thread.start()
        logger.info(f"API iniciada em http://{host}:{port}")

    # ── 11. Ativação inicial via --mode ──────────────────────────────────────
    event_bus.publish(PuckEvent(EventType.SYSTEM_STARTED, source="main"))

    if args.mode:
        logger.info(f"--mode '{args.mode}': ativando modo ao iniciar")
        launcher.launch_mode(args.mode)

    if args.no_audio:
        logger.info("--no-audio ativo: escuta de palmas desabilitada")
    else:
        logger.info("Aguardando sequência de palmas...")
        detector.start(callback=on_clap_sequence)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
