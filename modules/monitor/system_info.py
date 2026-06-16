"""
modules/monitor/system_info.py

Coleta métricas do sistema operacional.

Por que psutil:
    psutil é a biblioteca padrão de fato para métricas de sistema em Python.
    Funciona em Windows, Linux e macOS com a mesma API.
    Temperatura funciona em alguns sistemas — tratamos a ausência com graceful degradation.

Implementa: core.interfaces.SystemMonitor
"""

from typing import Optional
import psutil

from core.interfaces import SystemMonitor
from utils.logger import get_logger

logger = get_logger(__name__)


class PsutilSystemMonitor(SystemMonitor):
    """
    Implementação de SystemMonitor usando a biblioteca psutil.

    Todos os métodos retornam dados estruturados (dicts) pensando
    em serialização futura para JSON via FastAPI.
    """

    def get_cpu_usage(self) -> float:
        """
        Retorna uso de CPU em percentual.

        interval=1: mede por 1 segundo para ter uma leitura precisa.
        interval=None retornaria o valor desde a última chamada — impreciso.
        """
        return psutil.cpu_percent(interval=1)

    def get_memory_usage(self) -> dict:
        """
        Retorna uso de memória RAM.

        svmem.total e svmem.used estão em bytes — convertemos para GB
        para facilitar leitura e display futuro.
        """
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024 ** 3), 2),
            "used_gb": round(mem.used / (1024 ** 3), 2),
            "available_gb": round(mem.available / (1024 ** 3), 2),
            "percent": mem.percent,
        }

    def get_disk_usage(self, path: str = "/") -> dict:
        """
        Retorna uso do disco principal.

        Args:
            path: ponto de montagem a monitorar.
                  No Windows, use 'C:\\' em vez de '/'.
        """
        disk = psutil.disk_usage(path)
        return {
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "used_gb": round(disk.used / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "percent": disk.percent,
        }

    def get_network_info(self) -> dict:
        """
        Retorna bytes enviados e recebidos desde o boot do sistema.

        Útil para detectar uso anormal de rede no futuro.
        """
        net = psutil.net_io_counters()
        return {
            "bytes_sent_mb": round(net.bytes_sent / (1024 ** 2), 2),
            "bytes_recv_mb": round(net.bytes_recv / (1024 ** 2), 2),
        }

    def get_temperature(self) -> Optional[float]:
        """
        Retorna temperatura da CPU se disponível.

        psutil.sensors_temperatures() não funciona em todos os sistemas.
        Retornamos None em vez de lançar exceção — o caller decide o que fazer.
        """
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return None

            # Tenta chaves comuns — varia por hardware e OS
            for key in ("coretemp", "cpu_thermal", "k10temp"):
                if key in temps:
                    return temps[key][0].current

            return None

        except (AttributeError, NotImplementedError):
            # Windows frequentemente não suporta sensors_temperatures
            return None

    def get_full_report(self) -> dict:
        """
        Relatório completo do sistema.

        Este é o método que uma rota GET /metrics do FastAPI vai chamar.
        Já está estruturado para serialização JSON direta.
        """
        report = {
            "cpu": {
                "usage_percent": self.get_cpu_usage(),
                "cores": psutil.cpu_count(logical=True),
            },
            "memory": self.get_memory_usage(),
            "disk": self.get_disk_usage("C:\\" if psutil.WINDOWS else "/"),
            "network": self.get_network_info(),
            "temperature_celsius": self.get_temperature(),
        }

        logger.debug(f"Relatório do sistema coletado: CPU {report['cpu']['usage_percent']}%")
        return report
