"""
tests/test_launcher.py

Testes para modules/automation/launcher.py

Estratégia de mocking:
    - subprocess.Popen: substituído por um fake para não abrir nada de verdade
    - pathlib.Path.exists: simula que os executáveis existem
"""

from pathlib import Path

import pytest

from config.settings import Settings
from core.modes import ModeManager
from modules.automation.launcher import WindowsAppLauncher


class TestWindowsAppLauncher:
    def test_launch_success(self, settings: Settings, monkeypatch) -> None:
        launched = []

        def fake_popen(cmd, **kwargs):
            launched.append(cmd)

        monkeypatch.setattr(Path, "exists", lambda self: True)
        monkeypatch.setattr(
            "modules.automation.launcher.subprocess.Popen", fake_popen
        )

        launcher = WindowsAppLauncher(settings, ModeManager(settings))
        assert launcher.launch("vscode") is True
        assert launched == [["C:/fake/vscode.exe"]]

    def test_launch_app_not_configured(
        self, settings: Settings, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "modules.automation.launcher.subprocess.Popen",
            lambda *args, **kwargs: pytest.fail("Não deveria abrir nada"),
        )

        launcher = WindowsAppLauncher(settings, ModeManager(settings))
        assert launcher.launch("app_inexistente") is False

    def test_launch_missing_executable_returns_false(
        self, settings: Settings, monkeypatch
    ) -> None:
        monkeypatch.setattr(Path, "exists", lambda self: False)
        monkeypatch.setattr(
            "modules.automation.launcher.subprocess.Popen",
            lambda *args, **kwargs: pytest.fail("Não deveria abrir nada"),
        )

        launcher = WindowsAppLauncher(settings, ModeManager(settings))
        assert launcher.launch("vscode") is False

    def test_launch_expands_env_vars(
        self, settings: Settings, monkeypatch
    ) -> None:
        launched = []

        def fake_popen(cmd, **kwargs):
            launched.append(cmd)

        monkeypatch.setattr(Path, "exists", lambda self: True)
        monkeypatch.setattr(
            "modules.automation.launcher.subprocess.Popen", fake_popen
        )
        monkeypatch.setenv("USERNAME", "wkrod")

        launcher = WindowsAppLauncher(settings, ModeManager(settings))
        assert launcher.launch("opera") is True
        assert launched == [["C:/Users/wkrod/opera.exe"]]

    def test_launch_absolute_path_on_path_without_exists_check(
        self, settings: Settings, monkeypatch
    ) -> None:
        # 'wt.exe' não é caminho absoluto — não passa pela checagem de exists
        launched = []

        def fake_popen(cmd, **kwargs):
            launched.append(cmd)

        monkeypatch.setattr(Path, "exists", lambda self: False)
        monkeypatch.setattr(
            "modules.automation.launcher.subprocess.Popen", fake_popen
        )

        launcher = WindowsAppLauncher(settings, ModeManager(settings))
        assert launcher.launch("terminal") is True
        assert launched == [["wt.exe"]]

    def test_launch_file_not_found_returns_false(
        self, settings: Settings, monkeypatch
    ) -> None:
        def raise_not_found(cmd, **kwargs):
            raise FileNotFoundError(cmd)

        monkeypatch.setattr(Path, "exists", lambda self: True)
        monkeypatch.setattr(
            "modules.automation.launcher.subprocess.Popen", raise_not_found
        )

        launcher = WindowsAppLauncher(settings, ModeManager(settings))
        assert launcher.launch("vscode") is False

    def test_launch_permission_error_returns_false(
        self, settings: Settings, monkeypatch
    ) -> None:
        def raise_permission(cmd, **kwargs):
            raise PermissionError(cmd)

        monkeypatch.setattr(Path, "exists", lambda self: True)
        monkeypatch.setattr(
            "modules.automation.launcher.subprocess.Popen", raise_permission
        )

        launcher = WindowsAppLauncher(settings, ModeManager(settings))
        assert launcher.launch("vscode") is False

    def test_launch_mode_launches_all_apps(
        self, settings: Settings, monkeypatch
    ) -> None:
        launched = []

        def fake_popen(cmd, **kwargs):
            launched.append(cmd)

        monkeypatch.setattr(Path, "exists", lambda self: True)
        monkeypatch.setattr(
            "modules.automation.launcher.subprocess.Popen", fake_popen
        )

        launcher = WindowsAppLauncher(settings, ModeManager(settings))
        launcher.launch_mode("ads")

        assert launched == [
            ["C:/fake/vscode.exe"],
            ["C:/fake/spotify.exe"],
        ]

    def test_launch_mode_unknown_does_nothing(
        self, settings: Settings, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "modules.automation.launcher.subprocess.Popen",
            lambda *args, **kwargs: pytest.fail("Não deveria abrir nada"),
        )

        launcher = WindowsAppLauncher(settings, ModeManager(settings))
        launcher.launch_mode("nao_existe")

    def test_launch_mode_sets_current_mode(
        self, settings: Settings, monkeypatch
    ) -> None:
        monkeypatch.setattr(Path, "exists", lambda self: True)
        monkeypatch.setattr(
            "modules.automation.launcher.subprocess.Popen", lambda *a, **k: None
        )

        mode_manager = ModeManager(settings)
        launcher = WindowsAppLauncher(settings, mode_manager)

        launcher.launch_mode("ads")
        assert mode_manager.get_current_mode().name == "ads"

    def test_launch_mode_continues_on_partial_failure(
        self, settings: Settings, monkeypatch
    ) -> None:
        # vscode falha (arquivo não existe), spotify abre
        launched = []

        def fake_popen(cmd, **kwargs):
            launched.append(cmd)

        monkeypatch.setattr(
            Path,
            "exists",
            lambda self: str(self).endswith("spotify.exe"),
        )
        monkeypatch.setattr(
            "modules.automation.launcher.subprocess.Popen", fake_popen
        )

        launcher = WindowsAppLauncher(settings, ModeManager(settings))
        launcher.launch_mode("ads")

        assert launched == [["C:/fake/spotify.exe"]]
