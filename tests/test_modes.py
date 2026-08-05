"""
tests/test_modes.py

Testes para core/modes.py
"""

from config.settings import Settings
from core.modes import ModeManager, WorkMode


class TestModeManager:
    def test_list_modes(self, settings: Settings) -> None:
        manager = ModeManager(settings)
        assert set(manager.list_modes()) == {"ads", "gamer"}

    def test_get_mode_returns_workmode(self, settings: Settings) -> None:
        manager = ModeManager(settings)
        mode = manager.get_mode("ads")

        assert isinstance(mode, WorkMode)
        assert mode.name == "ads"
        assert mode.display_name == "Modo ADS"
        assert mode.apps == ["vscode", "spotify"]

    def test_get_mode_missing_returns_none(self, settings: Settings) -> None:
        manager = ModeManager(settings)
        assert manager.get_mode("nao_existe") is None

    def test_current_mode_is_none_initially(self, settings: Settings) -> None:
        manager = ModeManager(settings)
        assert manager.get_current_mode() is None

    def test_activate_mode_sets_current(self, settings: Settings) -> None:
        manager = ModeManager(settings)
        mode = manager.activate_mode("gamer")

        assert mode is not None
        assert manager.get_current_mode().name == "gamer"

    def test_activate_invalid_mode_returns_none(self, settings: Settings) -> None:
        manager = ModeManager(settings)
        assert manager.activate_mode("nao_existe") is None
        assert manager.get_current_mode() is None

    def test_deactivate_clears_current(self, settings: Settings) -> None:
        manager = ModeManager(settings)
        manager.activate_mode("ads")
        assert manager.get_current_mode() is not None

        manager.deactivate()
        assert manager.get_current_mode() is None
