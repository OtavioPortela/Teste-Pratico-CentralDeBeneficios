"""Cliente HTTP da API pública do Hacker News.

Sabe falar com a API e nada mais: não conhece SQL, watermark nem métricas.
Uma resposta `null` é um resultado legítimo (item inexistente ou removido) e
volta como `None`; falha técnica depois das tentativas vira `ErroAPI`.
"""

import logging
import time
from typing import Any

import requests

from .config import Config
from .erros import ErroAPI

logger = logging.getLogger(__name__)

# Situações que costumam se resolver sozinhas e por isso merecem nova tentativa.
STATUS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})


class ClienteHackerNews:
    """Acesso aos endpoints usados pela carga.

    Usa uma `requests.Session` porque a carga faz dezenas de chamadas
    sequenciais ao mesmo host e a sessão reaproveita a conexão TCP/TLS.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._sessao = requests.Session()

    def __enter__(self) -> "ClienteHackerNews":
        return self

    def __exit__(self, *_) -> None:
        self.fechar()

    def fechar(self) -> None:
        self._sessao.close()

    def maxitem(self) -> int:
        """Maior ID existente no Hacker News neste momento."""
        valor = self._obter("maxitem.json", descricao="maxitem")
        if not isinstance(valor, int):
            raise ErroAPI(f"maxitem inválido: {valor!r}")
        return valor

    def item(self, identificador: int) -> dict[str, Any] | None:
        """Item pelo ID. Devolve `None` quando a API responde `null`."""
        valor = self._obter(
            f"item/{identificador}.json", descricao=f"item {identificador}"
        )
        if valor is None:
            return None
        if not isinstance(valor, dict):
            raise ErroAPI(f"item {identificador} veio em formato inesperado: {valor!r}")
        return valor

    def _obter(self, caminho: str, descricao: str) -> Any:
        """Faz o GET com timeout, tentativas limitadas e backoff crescente.

        Repete apenas o que tem chance de melhorar sozinho: timeout, erro de
        conexão, status transitório e corpo ilegível. Um 4xx definitivo falha
        na hora, porque repetir não mudaria a resposta.
        """
        url = f"{self._config.url_base}/{caminho}"
        for tentativa in range(1, self._config.tentativas + 1):
            try:
                resposta = self._sessao.get(url, timeout=self._config.timeout)
                if resposta.status_code in STATUS_TRANSITORIOS:
                    motivo = f"HTTP {resposta.status_code}"
                else:
                    resposta.raise_for_status()
                    return resposta.json()
            except requests.Timeout:
                motivo = "timeout"
            except requests.ConnectionError:
                motivo = "erro de conexão"
            except requests.HTTPError as erro:
                raise ErroAPI(
                    f"{descricao}: HTTP {erro.response.status_code} (definitivo)"
                ) from erro
            except ValueError as erro:  # corpo que não é JSON válido
                motivo = f"resposta ilegível ({erro})"

            if tentativa == self._config.tentativas:
                raise ErroAPI(
                    f"{descricao}: {motivo} após {self._config.tentativas} tentativas"
                )
            espera = self._config.backoff_inicial * 2 ** (tentativa - 1)
            logger.warning(
                "%s: tentativa %d de %d falhou (%s); nova tentativa em %.1fs",
                descricao,
                tentativa,
                self._config.tentativas,
                motivo,
                espera,
            )
            time.sleep(espera)
