"""
core/interfaces.py

Define os contratos (ABCs) que todos os módulos do Puck devem seguir.

Por que isso existe:
    Em vez de os módulos dependerem uns dos outros diretamente, eles dependem
    destes contratos. Isso permite trocar implementações sem quebrar o sistema.

    Exemplo prático: hoje o detector de palmas usa pico de áudio.
    Amanhã, pode usar YAMNet (ML). O contrato não muda — só a implementação.

Princípio aplicado: Dependency Inversion (SOLID — D)
"""

from abc import ABC, abstractmethod
from typing import Callable


class AudioDetector(ABC):
    """
    Contrato para qualquer detector baseado em áudio.
    
    Qualquer implementação — pico de som, ML, wake word — deve seguir
    esta interface. O orquestrador (main.py) não precisa saber qual
    implementação está sendo usada.
    """

    @abstractmethod
    def start(self, callback: Callable[[], None]) -> None:
        """
        Inicia a escuta contínua.

        Args:
            callback: função a ser chamada quando o evento for detectado.
                      O detector não decide o que fazer — só avisa.
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """Para a escuta e libera recursos (microfone, threads)."""
        ...


class AppLauncher(ABC):
    """
    Contrato para qualquer sistema de abertura de aplicativos.
    
    Permite criar implementações diferentes por OS (Windows, Linux, macOS)
    sem mudar quem chama o launcher.
    """

    @abstractmethod
    def launch(self, app_name: str) -> bool:
        """
        Abre um aplicativo pelo nome configurado.

        Args:
            app_name: chave do aplicativo no config.yaml (ex: 'vscode')

        Returns:
            True se abriu com sucesso, False caso contrário.
        """
        ...

    @abstractmethod
    def launch_mode(self, mode_name: str) -> None:
        """
        Abre todos os aplicativos de um modo de trabalho.

        Args:
            mode_name: nome do modo (ex: 'ads', 'estudo', 'gamer')
        """
        ...


class SystemMonitor(ABC):
    """
    Contrato para coleta de métricas do sistema.
    
    Quando o FastAPI entrar, a rota /metrics vai chamar este contrato
    sem se importar com a implementação por baixo.
    """

    @abstractmethod
    def get_cpu_usage(self) -> float:
        """Retorna uso de CPU em percentual (0.0 a 100.0)."""
        ...

    @abstractmethod
    def get_memory_usage(self) -> dict:
        """
        Retorna informações de memória RAM.

        Returns:
            dict com 'total_gb', 'used_gb', 'percent'
        """
        ...

    @abstractmethod
    def get_disk_usage(self) -> dict:
        """
        Retorna informações de disco.

        Returns:
            dict com 'total_gb', 'used_gb', 'percent'
        """
        ...

    @abstractmethod
    def get_full_report(self) -> dict:
        """
        Retorna relatório completo do sistema.
        Útil para APIs e dashboards futuros.
        """
        ...
