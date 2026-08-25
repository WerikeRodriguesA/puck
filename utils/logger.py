"""
utils/logger.py

Sistema de logs centralizado do Puck.

Por que não usar print():
    print() não tem nível (INFO vs ERROR), não salva em arquivo,
    não tem timestamp automático, não é desligável em produção.
    O módulo logging da stdlib resolve tudo isso sem dependência externa.

Por que uma função factory e não um logger global:
    Cada módulo pede seu próprio logger com seu nome.
    No log aparece: [audio.detector] vs [modules.automation.launcher]
    Isso torna o debug muito mais rápido.

Uso:
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Sistema iniciado")
    logger.error("Falha ao abrir app", exc_info=True)
"""

import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
from typing import Optional


# Logger raiz do Puck — todos os sub-loggers herdam dele
_ROOT_LOGGER_NAME = "puck"

# Controle para não registrar handlers duplicados
_configured = False


def configure_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_dir: Optional[Path] = None,
    log_filename: str = "puck.log",
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> None:
    """
    Configura o sistema de logging do Puck.

    Deve ser chamado UMA VEZ na inicialização (em main.py).
    Configura dois handlers:
        - Console: exibe logs coloridos no terminal
        - Arquivo: salva todos os logs em disco com rotação automática (se habilitado)

    Args:
        level: nível mínimo de log (DEBUG, INFO, WARNING, ERROR)
        log_to_file: se True, salva logs em arquivo
        log_dir: diretório para salvar o arquivo de log
        log_filename: nome do arquivo de log
        max_bytes: tamanho máximo em bytes antes de rotacionar (padrão: 5MB)
        backup_count: quantidade de arquivos de backup mantidos (padrão: 3)
    """
    global _configured
    if _configured:
        return  # Evita registrar handlers duplicados em chamadas repetidas

    root_logger = logging.getLogger(_ROOT_LOGGER_NAME)
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Formato: [15:30:42] INFO     audio.detector — Palma detectada
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    # Handler de console — sempre ativo
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Handler de arquivo com rotação — opcional
    if log_to_file and log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_path = log_dir / log_filename

        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger filho do logger raiz do Puck.

    Args:
        name: geralmente __name__ do módulo que está chamando.
              Ex: 'puck.modules.audio.detector'

    Returns:
        Logger configurado e pronto para uso.
    """
    # Se o name já começa com "puck.", usa direto
    # Senão, prefixamos para manter hierarquia
    if not name.startswith(_ROOT_LOGGER_NAME):
        name = f"{_ROOT_LOGGER_NAME}.{name}"

    return logging.getLogger(name)
