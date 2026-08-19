"""Configuração da execução: caminhos do projeto e parâmetros do navegador."""

from dataclasses import dataclass
from pathlib import Path

URL_DESAFIO = "https://rpachallenge.com/"
NOME_PLANILHA = "challenge.xlsx"

RAIZ = Path(__file__).resolve().parent.parent
DIR_DADOS = RAIZ / "data"
DIR_ARTIFACTS = RAIZ / "artifacts"


@dataclass(frozen=True)
class Config:
    """Parâmetros de uma execução."""

    headless: bool = True
    timeout: int = 20
    timeout_download: int = 30
    url: str = URL_DESAFIO
    dir_dados: Path = DIR_DADOS
    dir_artifacts: Path = DIR_ARTIFACTS

    @property
    def planilha(self) -> Path:
        return self.dir_dados / NOME_PLANILHA

    def preparar_diretorios(self) -> None:
        self.dir_dados.mkdir(parents=True, exist_ok=True)
        self.dir_artifacts.mkdir(parents=True, exist_ok=True)
