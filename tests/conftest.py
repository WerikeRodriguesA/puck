"""
tests/conftest.py

Fixtures compartilhadas pelos testes do Puck.

Princípio adotado:
    Os testes NUNCA leem o config/config.yaml real.
    Cada suite usa um config.yaml fake em um diretório temporário.
    Isso isola os testes das configurações da máquina do autor
    e permite testar cenários que não existem no config real.
"""

from pathlib import Path

import pytest
import yaml

from config.settings import Settings


@pytest.fixture
def fake_config(tmp_path: Path) -> dict:
    """Configuração YAML fake usada pela maioria dos testes."""
    return {
        "audio": {
            "sample_rate": 44100,
            "chunk_size": 1024,
            "clap_threshold": 3000,
            "clap_debounce_ms": 150,
            "sequence_window_ms": 1200,
            "activation_cooldown_seconds": 5.0,
        },
        "apps": {
            "vscode": {
                "display_name": "VS Code",
                "path": "C:/fake/vscode.exe",
            },
            "spotify": {
                "display_name": "Spotify",
                "path": "C:/fake/spotify.exe",
            },
            "terminal": {
                "display_name": "Windows Terminal",
                "path": "wt.exe",
            },
            "opera": {
                "display_name": "Opera GX",
                "path": "C:/Users/%USERNAME%/opera.exe",
            },
        },
        "modes": {
            "ads": {
                "display_name": "Modo ADS",
                "apps": ["vscode", "spotify"],
            },
            "gamer": {
                "display_name": "Modo Gamer",
                "apps": ["terminal"],
            },
        },
        "default_mode": "ads",
        "logging": {
            "level": "DEBUG",
            "log_to_file": False,
            "log_filename": "puck_test.log",
        },
    }


@pytest.fixture
def settings(tmp_path: Path, fake_config: dict) -> Settings:
    """Instância de Settings apontando para o config.yaml fake."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.safe_dump(fake_config, allow_unicode=True),
        encoding="utf-8",
    )
    return Settings(config_path=config_file)
