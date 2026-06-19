"""
modules/audio/detector.py

Detecção de palmas por análise de amplitude de áudio.

ALGORITMO ATUAL — detecção por pico de amplitude:
    Problema resolvido nesta versão:
        Uma única palma física gera múltiplos chunks de áudio com amplitude
        alta (o som tem decay de ~20-50ms). O algoritmo antigo contava cada
        chunk alto como uma palma separada, causando disparos duplos/triplos
        de um único evento físico.

    Solução implementada em duas camadas:

    Camada 1 — Debounce por palma individual (clap_debounce_ms):
        Após detectar uma palma, ignora qualquer pico por X ms.
        Isso garante que uma palma física = exatamente 1 contagem.

    Camada 2 — Janela de sequência (sequence_window_ms):
        Após a primeira palma, um timer começa a contar.
        Novas palmas dentro da janela incrementam o contador.
        Quando a janela expira, o total é enviado ao callback.
        Isso permite distinguir 2, 3, 4 palmas sem ambiguidade.

LIMITAÇÕES CONHECIDAS (documentadas para evolução futura):
    - Falsos positivos em ambientes barulhentos
    - Não distingue palma de outros sons altos de curta duração
    - V2 sugerida: análise de frequência (FFT)
    - V3 sugerida: classificação por ML (YAMNet / TensorFlow Lite)

Implementa: core.interfaces.AudioDetector
"""

import threading
import time
from typing import Callable, Optional

import pyaudio
import numpy as np

from core.interfaces import AudioDetector
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger(__name__)


class ClapDetector(AudioDetector):
    """
    Detecta sequências de palmas e reporta a contagem ao callback.

    Comportamento esperado:
        👏👏     → callback(2)
        👏👏👏   → callback(3)
        👏👏👏👏 → callback(4)

    O ClapDetector NÃO sabe o que cada contagem significa.
    Ele apenas conta e entrega. Quem decide o que fazer é o main.py.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        audio_cfg = settings.audio_config

        # Configurações de captura
        self._sample_rate: int = audio_cfg.get("sample_rate", 44100)
        self._chunk_size: int = audio_cfg.get("chunk_size", 1024)
        self._threshold: int = audio_cfg.get("clap_threshold", 3000)

        # Debounce: tempo mínimo entre duas palmas individuais
        # Evita que o decay de uma palma física seja contado como 2 palmas
        self._debounce_ms: int = audio_cfg.get("clap_debounce_ms", 150)

        # Janela de sequência: tempo de espera após a primeira palma
        # O sistema aguarda este tempo antes de encerrar a contagem
        self._sequence_window_ms: int = audio_cfg.get("sequence_window_ms", 1200)

        # Cooldown global: após executar um modo, ignora novas detecções
        # Evita abrir múltiplas instâncias por sequências acidentais
        self._activation_cooldown: float = audio_cfg.get(
            "activation_cooldown_seconds", 5.0
        )

        # Estado interno
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._listen_thread: Optional[threading.Thread] = None
        self._running: bool = False

        # Controle de sequência — acessados por múltiplas threads
        self._clap_count: int = 0
        self._last_clap_time: float = 0.0       # Última palma individual (debounce)
        self._last_activation_time: float = 0.0  # Última ativação completa (cooldown)
        self._sequence_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()  # Protege o estado compartilhado

    # ──────────────────────────────────────────────────────────────────────────
    # Interface pública (contrato AudioDetector)
    # ──────────────────────────────────────────────────────────────────────────

    def start(self, callback: Callable[[int], None]) -> None:
        """
        Inicia a escuta contínua em thread separada.

        Args:
            callback: chamado com o total de palmas ao final de cada sequência.
        """
        if self._running:
            logger.warning("ClapDetector já está rodando")
            return

        self._running = True
        self._listen_thread = threading.Thread(
            target=self._listen_loop,
            args=(callback,),
            daemon=True,
            name="clap-detector",
        )
        self._listen_thread.start()

        logger.info(
            f"ClapDetector iniciado | "
            f"threshold={self._threshold} | "
            f"debounce={self._debounce_ms}ms | "
            f"janela={self._sequence_window_ms}ms | "
            f"cooldown={self._activation_cooldown}s"
        )

    def stop(self) -> None:
        """Para a escuta, cancela timers pendentes e libera recursos."""
        self._running = False

        # Cancela timer de sequência se estiver ativo
        with self._lock:
            if self._sequence_timer:
                self._sequence_timer.cancel()
                self._sequence_timer = None

        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        if self._pyaudio:
            self._pyaudio.terminate()
            self._pyaudio = None

        if self._listen_thread:
            self._listen_thread.join(timeout=2.0)
            self._listen_thread = None

        logger.info("ClapDetector parado")

    # ──────────────────────────────────────────────────────────────────────────
    # Lógica interna
    # ──────────────────────────────────────────────────────────────────────────

    def _listen_loop(self, callback: Callable[[int], None]) -> None:
        """
        Loop de captura de áudio. Roda em thread dedicada.

        Responsabilidade única: ler chunks e detectar picos.
        A lógica de contagem e temporização fica em métodos separados.
        """
        try:
            self._pyaudio = pyaudio.PyAudio()
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self._sample_rate,
                input=True,
                frames_per_buffer=self._chunk_size,
            )

            logger.debug("Stream de áudio aberto")

            while self._running:
                raw = self._stream.read(
                    self._chunk_size,
                    exception_on_overflow=False,
                )
                audio_data = np.frombuffer(raw, dtype=np.int16)
                amplitude = int(np.max(np.abs(audio_data)))

                if amplitude > self._threshold:
                    self._on_peak_detected(amplitude, callback)

        except OSError as e:
            logger.error(f"Erro ao acessar microfone: {e}")
            logger.error("Verifique se o microfone está conectado e com permissão")
        except Exception as e:
            logger.error(f"Erro inesperado no ClapDetector: {e}", exc_info=True)
        finally:
            self._running = False

    def _on_peak_detected(
        self, amplitude: int, callback: Callable[[int], None]
    ) -> None:
        """
        Chamado a cada chunk com amplitude acima do threshold.

        Aplica as duas camadas de proteção:
            1. Cooldown global — ignora se uma ativação acabou de ocorrer
            2. Debounce individual — ignora se é o decay da palma anterior

        Se passar pelas duas camadas, incrementa o contador e
        (re)inicia o timer de janela de sequência.
        """
        now = time.time()

        with self._lock:
            # Camada 1: Cooldown global
            # Se uma ativação ocorreu há menos de N segundos, ignora tudo
            cooldown_elapsed = now - self._last_activation_time
            if cooldown_elapsed < self._activation_cooldown:
                remaining = self._activation_cooldown - cooldown_elapsed
                logger.debug(f"Cooldown ativo — ignorando pico ({remaining:.1f}s restantes)")
                return

            # Camada 2: Debounce por palma individual
            # Se o último pico foi há menos de debounce_ms, é o mesmo som físico
            debounce_elapsed_ms = (now - self._last_clap_time) * 1000
            if debounce_elapsed_ms < self._debounce_ms:
                logger.debug(
                    f"Debounce — decay da palma anterior ignorado "
                    f"({debounce_elapsed_ms:.0f}ms < {self._debounce_ms}ms)"
                )
                return

            # Palma válida — registra e incrementa contador
            self._last_clap_time = now
            self._clap_count += 1
            count_snapshot = self._clap_count

            logger.debug(
                f"Palma {count_snapshot} detectada (amplitude={amplitude})"
            )

            # Reinicia o timer de janela a cada palma nova
            # Isso garante que o timer sempre conta a partir da ÚLTIMA palma
            if self._sequence_timer:
                self._sequence_timer.cancel()

            self._sequence_timer = threading.Timer(
                interval=self._sequence_window_ms / 1000,
                function=self._on_sequence_complete,
                args=(callback,),
            )
            self._sequence_timer.daemon = True
            self._sequence_timer.start()

    def _on_sequence_complete(self, callback: Callable[[int], None]) -> None:
        """
        Chamado pelo timer quando a janela de sequência expira.

        Nesse ponto, o usuário parou de bater palmas.
        Captura o total, reseta o estado e dispara o callback.

        Este método roda na thread do Timer — por isso usa lock.
        """
        with self._lock:
            total = self._clap_count

            if total == 0:
                return

            self._clap_count = 0
            self._sequence_timer = None
            self._last_activation_time = time.time()

        logger.info(f"Sequência encerrada: {total} palma(s) detectada(s)")

        # Callback fora do lock — evita deadlock se o callback demorar
        callback(total)