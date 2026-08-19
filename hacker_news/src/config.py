"""Configuração da carga: endpoints, caminhos, timeouts e política de retry."""

from dataclasses import dataclass
from pathlib import Path

URL_BASE = "https://hacker-news.firebaseio.com/v0"
LIMITE_INICIAL = 100

RAIZ = Path(__file__).resolve().parent.parent
DIR_DADOS = RAIZ / "data"
DIR_ARTIFACTS = RAIZ / "artifacts"
BANCO = DIR_DADOS / "hacker_news.db"


@dataclass(frozen=True)
class Config:
    """Parâmetros de uma execução da carga."""

    url_base: str = URL_BASE
    banco: Path = BANCO
    dir_artifacts: Path = DIR_ARTIFACTS
    limite_inicial: int = LIMITE_INICIAL
    timeout: float = 10.0
    tentativas: int = 3
    backoff_inicial: float = 0.5

    def preparar_diretorios(self) -> None:
        self.banco.parent.mkdir(parents=True, exist_ok=True)
        self.dir_artifacts.mkdir(parents=True, exist_ok=True)
