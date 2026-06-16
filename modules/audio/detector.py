"""
modules/audio/detector.py

Detecção de palmas por análise de amplitude de áudio.

Decisão arquitetural — por que esta abordagem e quais são seus limites:
    Esta implementação usa detecção de pico sonoro (amplitude máxima do chunk).
    É a abordagem mais simples e funciona em ambientes silenciosos.

    LIMITAÇÕES CONHECIDAS:
    - Falsos positivos em ambientes barulhentos (música alta, barulho de rua)
    - Sensibilidade depende do hardware do microfone
    - Não distingue palma de outros sons altos

    CAMINHO DE EVOLUÇÃO (sem quebrar a interface):
    - V2: Análise de frequência (FFT) — palmas têm padrão espectral específico
    - V3: Modelo de ML leve como YAMNet (TensorFlow Lite) — classificação real
    Ambas as versões substituiriam apenas este arquivo — o resto do sistema
    não saberia que mudou nada.

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
    Detecta duas palmas consecutivas dentro de uma janela de tempo.

    Algoritmo:
        1. Captura chunks de áudio continuamente
        2. Calcula a amplitude máxima do chunk (np.max(np.abs(data)))
        3. Se amplitude > threshold: registra como "palma detectada"
        4. Se duas palmas forem detectadas dentro do intervalo configurado:
           dispara o callback
        5. Aguarda um cooldown antes de aceitar novo par de palmas
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._audio_config = settings.audio_config

        self._sample_rate: int = self._audio_config.get("sample_rate", 44100)
        self._chunk_size: int = self._audio_config.get("chunk_size", 1024)
        self._threshold: int = self._audio_config.get("clap_threshold", 3000)
        self._interval_ms: int = self._audio_config.get("double_clap_interval_ms", 800)

        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._thread: Optional[threading.Thread] = None
        self._running: bool = False

        # Estado interno de detecção
        self._last_clap_time: float = 0.0
        self._cooldown_seconds: float = 1.5  # Evita tripla-detecção falsa

    def start(self, callback: Callable[[], None]) -> None:
        """
        Inicia a escuta em uma thread separada para não bloquear o programa.

        Args:
            callback: função chamada quando duas palmas são detectadas.
                      Não passa argumentos — o detector só avisa.
        """
        if self._running:
            logger.warning("ClapDetector já está rodando")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._listen_loop,
            args=(callback,),
            daemon=True,  # daemon=True: a thread morre com o programa principal
            name="clap-detector",
        )
        self._thread.start()
        logger.info(
            f"ClapDetector iniciado "
            f"(threshold={self._threshold}, intervalo={self._interval_ms}ms)"
        )

    def stop(self) -> None:
        """Para a escuta e libera recursos de áudio."""
        self._running = False

        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        if self._pyaudio:
            self._pyaudio.terminate()
            self._pyaudio = None

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        logger.info("ClapDetector parado")

    def _listen_loop(self, callback: Callable[[], None]) -> None:
        """
        Loop principal de captura e análise de áudio.

        Roda em thread separada. Captura chunks, analisa amplitude
        e gerencia o estado de detecção de par de palmas.
        """
        try:
            self._pyaudio = pyaudio.PyAudio()
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,   # 16-bit PCM — padrão e eficiente
                channels=1,               # Mono — suficiente para detecção
                rate=self._sample_rate,
                input=True,
                frames_per_buffer=self._chunk_size,
            )

            logger.debug("Stream de áudio aberto com sucesso")
            clap_count = 0
            first_clap_time = 0.0

            while self._running:
                # Lê um chunk de áudio cru (bytes)
                raw_data = self._stream.read(
                    self._chunk_size,
                    exception_on_overflow=False,  # Evita crash se buffer cheio
                )

                # Converte bytes para array numpy de inteiros 16-bit
                audio_data = np.frombuffer(raw_data, dtype=np.int16)

                # Amplitude máxima do chunk — nossa métrica de "barulho alto"
                amplitude = np.max(np.abs(audio_data))

                if amplitude > self._threshold:
                    now = time.time()

                    # Cooldown: ignora palmas muito próximas da última detecção completa
                    if (now - self._last_clap_time) < self._cooldown_seconds:
                        continue

                    if clap_count == 0:
                        # Primeira palma detectada
                        clap_count = 1
                        first_clap_time = now
                        logger.debug(f"Palma 1 detectada (amplitude={amplitude})")

                    elif clap_count == 1:
                        elapsed_ms = (now - first_clap_time) * 1000

                        if elapsed_ms <= self._interval_ms:
                            # Segunda palma dentro do intervalo — ativação!
                            logger.info(
                                f"Dupla palma detectada! "
                                f"(intervalo={elapsed_ms:.0f}ms)"
                            )
                            clap_count = 0
                            self._last_clap_time = now
                            callback()  # Dispara a ação configurada
                        else:
                            # Segunda palma fora do intervalo — recomeça
                            logger.debug(
                                f"Palma fora do intervalo ({elapsed_ms:.0f}ms > "
                                f"{self._interval_ms}ms), reiniciando contagem"
                            )
                            clap_count = 1
                            first_clap_time = now

        except OSError as e:
            logger.error(f"Erro ao acessar microfone: {e}")
            logger.error("Verifique se o microfone está conectado e com permissão de acesso")
        except Exception as e:
            logger.error(f"Erro inesperado no ClapDetector: {e}", exc_info=True)
        finally:
            self._running = False
