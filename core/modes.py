"""
core/modes.py

Define e valida os modos de trabalho do Puck.

Responsabilidade deste módulo:
    Conhecer as regras de negócio dos modos — quais apps fazem parte
    de cada modo, qual modo está ativo, como trocar de modo.

    NÃO é responsabilidade deste módulo abrir aplicativos.
    Isso é separação de responsabilidades: o core sabe O QUE fazer,
    o módulo de automação sabe COMO fazer.
"""

from dataclasses import dataclass
from typing import Optional
from config.settings import Settings


@dataclass
class WorkMode:
    """
    Representa um modo de trabalho configurado.

    name: identificador interno (ex: 'ads')
    display_name: nome amigável para logs e UI futura (ex: 'Modo ADS')
    apps: lista de chaves de aplicativos a abrir (mapeadas no config.yaml)
    """

    name: str
    display_name: str
    apps: list[str]


class ModeManager:
    """
    Gerencia os modos de trabalho do Puck.

    Carrega os modos do arquivo de configuração e mantém o estado
    do modo atual. Stateful por design — há sempre um modo ativo (ou nenhum).
    """

    def __init__(self, settings: Settings) -> None:
        """
        Args:
            settings: instância de Settings já carregada.
                      ModeManager não lê config diretamente — recebe pronto.
                      Isso é Dependency Injection: facilita testes unitários.
        """
        self._settings = settings
        self._current_mode: Optional[WorkMode] = None
        self._modes: dict[str, WorkMode] = self._load_modes()

    def _load_modes(self) -> dict[str, WorkMode]:
        """
        Lê os modos do config.yaml e os converte em objetos WorkMode.

        Returns:
            Dicionário com nome do modo como chave e WorkMode como valor.
        """
        raw_modes = self._settings.get("modes", {})
        modes = {}

        for name, data in raw_modes.items():
            modes[name] = WorkMode(
                name=name,
                display_name=data.get("display_name", name.capitalize()),
                apps=data.get("apps", []),
            )

        return modes

    def get_mode(self, mode_name: str) -> Optional[WorkMode]:
        """
        Retorna um modo pelo nome.

        Returns:
            WorkMode se encontrado, None caso contrário.
        """
        return self._modes.get(mode_name)

    def activate_mode(self, mode_name: str) -> Optional[WorkMode]:
        """
        Ativa um modo de trabalho.

        Args:
            mode_name: nome do modo a ativar

        Returns:
            WorkMode ativado, ou None se o modo não existir.
        """
        mode = self.get_mode(mode_name)
        if mode:
            self._current_mode = mode
        return mode

    def get_current_mode(self) -> Optional[WorkMode]:
        """Retorna o modo atualmente ativo."""
        return self._current_mode

    def list_modes(self) -> list[str]:
        """Retorna lista com os nomes de todos os modos disponíveis."""
        return list(self._modes.keys())

    def deactivate(self) -> None:
        """Desativa o modo atual."""
        self._current_mode = None
