"""
tests/test_settings.py

Testes para config/settings.py
"""

from pathlib import Path

import pytest

from config.settings import Settings


class TestSettings:
    def test_loads_default_mode(self, settings: Settings) -> None:
        assert settings.get("default_mode") == "ads"

    def test_get_with_default_when_key_missing(self, settings: Settings) -> None:
        assert settings.get("inexistente", "fallback") == "fallback"

    def test_get_returns_none_when_missing_without_default(
        self, settings: Settings
    ) -> None:
        assert settings.get("inexistente") is None

    def test_get_app_path(self, settings: Settings) -> None:
        assert settings.get_app_path("vscode") == "C:/fake/vscode.exe"

    def test_get_app_path_missing_returns_none(self, settings: Settings) -> None:
        assert settings.get_app_path("app_inexistente") is None

    def test_missing_config_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            Settings(config_path=tmp_path / "nao_existe.yaml")

    def test_audio_config_returns_configured_values(
        self, settings: Settings
    ) -> None:
        audio = settings.audio_config
        assert audio["sample_rate"] == 44100
        assert audio["chunk_size"] == 1024

    def test_audio_config_defaults_when_empty(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("modes: {}\n", encoding="utf-8")

        s = Settings(config_path=config_file)
        audio = s.audio_config

        assert audio["sample_rate"] == 44100
        assert audio["clap_threshold"] == 3000

    def test_empty_yaml_does_not_crash(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("", encoding="utf-8")

        s = Settings(config_path=config_file)
        assert s.get("modes", {}) == {}

    def test_validate_success(self, settings: Settings) -> None:
        errors = settings.validate()
        assert errors == []

    def test_validate_detects_unconfigured_app_in_mode(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
apps:
  vscode:
    path: "C:/Code.exe"
modes:
  dev:
    apps:
      - vscode
      - app_desconhecido
""", encoding="utf-8")
        s = Settings(config_path=config_file)
        errors = s.validate()
        assert any("app_desconhecido" in err for err in errors)

    def test_validate_detects_invalid_clap_mode(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
apps:
  vscode:
    path: "C:/Code.exe"
modes:
  dev:
    apps:
      - vscode
clap_modes:
  2: dev
  3: modo_inexistente
""", encoding="utf-8")
        s = Settings(config_path=config_file)
        errors = s.validate()
        assert any("modo_inexistente" in err for err in errors)

    def test_validate_raise_on_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("default_mode: modo_invalido\n", encoding="utf-8")
        s = Settings(config_path=config_file)
        with pytest.raises(ValueError):
            s.validate(raise_on_error=True)

