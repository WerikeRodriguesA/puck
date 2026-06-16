"""
config/settings.py

Lê, valida e fornece acesso às configurações do Puck.

Por que existe este módulo e não só abrir o YAML direto:
    Se amanhã você quiser mudar de YAML para TOML, ou adicionar validação
    de schema, ou carregar de variável de ambiente — você muda aqui.
    O resto do sistema nunca soube que era YAML.

    Singleton por design: o arquivo é lido uma vez, na inicialização.
    Todos os módulos recebem a mesma instância via injeção de dependência.
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml


# Caminho base do projeto — resolve independente de onde o script é chamado
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"
LOGS_DIR = BASE_DIR / "logs"


class Settings:
    """
    Gerencia as configurações do projeto Puck.

    Carrega o config.yaml e expõe os valores de forma segura.
    Em caso de chave ausente, retorna defaults razoáveis em vez de explodir.
    """

    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        """
        Args:
            config_path: caminho para o config.yaml.
                         Pode ser sobrescrito em testes para usar um config fake.
        """
        self._config_path = config_path
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        """
        Lê o arquivo YAML e armazena em memória.

        Lança FileNotFoundError com mensagem clara se o arquivo não existir.
        Isso é melhor do que um KeyError genérico mais tarde.
        """
        if not self._config_path.exists():
            raise FileNotFoundError(
                f"Arquivo de configuração não encontrado: {self._config_path}\n"
                f"Copie o config.yaml.example para config/config.yaml e ajuste."
            )

        with open(self._config_path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Acessa uma configuração pelo nome da chave raiz.

        Args:
            key: chave no nível raiz do YAML (ex: 'modes', 'apps', 'audio')
            default: valor retornado se a chave não existir

        Returns:
            Valor configurado ou default.
        """
        return self._data.get(key, default)

    def get_app_path(self, app_name: str) -> Optional[str]:
        """
        Retorna o caminho de um aplicativo configurado.

        Args:
            app_name: chave do app no config.yaml (ex: 'vscode', 'spotify')

        Returns:
            Caminho do executável ou None se não configurado.
        """
        apps = self._data.get("apps", {})
        return apps.get(app_name, {}).get("path")

    @property
    def logs_dir(self) -> Path:
        """Retorna o diretório de logs, garantindo que exista."""
        LOGS_DIR.mkdir(exist_ok=True)
        return LOGS_DIR

    @property
    def audio_config(self) -> dict:
        """Retorna configurações de áudio com defaults seguros."""
        return self._data.get("audio", {
            "sample_rate": 44100,
            "chunk_size": 1024,
            "clap_threshold": 3000,
            "double_clap_interval_ms": 800,
        })

    def __repr__(self) -> str:
        return f"Settings(config='{self._config_path}')"
