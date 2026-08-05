"""
tests/test_main.py

Testes para a interpretação de argumentos de linha de comando em main.py.
"""

import main


class TestParseArgs:
    def test_defaults(self) -> None:
        args = main.parse_args([])
        assert args.config is None
        assert args.mode is None
        assert args.no_audio is False
        assert args.list_modes is False

    def test_config(self) -> None:
        args = main.parse_args(["--config", "outro.yaml"])
        assert args.config == "outro.yaml"

    def test_mode(self) -> None:
        args = main.parse_args(["--mode", "ads"])
        assert args.mode == "ads"

    def test_no_audio_flag(self) -> None:
        args = main.parse_args(["--no-audio"])
        assert args.no_audio is True

    def test_list_modes_flag(self) -> None:
        args = main.parse_args(["--list-modes"])
        assert args.list_modes is True

    def test_combined_flags(self) -> None:
        args = main.parse_args(["--no-audio", "--mode", "gamer"])
        assert args.no_audio is True
        assert args.mode == "gamer"
