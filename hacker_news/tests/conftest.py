"""Fixtures compartilhadas: banco temporário e dublês da API."""

import sqlite3

import pytest

from src.banco import abrir
from src.erros import ErroAPI

# Payload real de uma story do Hacker News (item 8863), usado como referência.
STORY = {
    "by": "dhouston",
    "descendants": 71,
    "id": 8863,
    "kids": [8952, 9224, 8917],
    "score": 104,
    "time": 1175714200,
    "title": "My YC app: Dropbox - Throw away your USB drive",
    "type": "story",
    "url": "http://www.getdropbox.com/u/2/screencast.html",
}

# Comentário: não tem title/url/score, tem parent e text.
COMENTARIO = {
    "by": "norvig",
    "id": 2921983,
    "kids": [2922097, 2922429],
    "parent": 2921506,
    "text": "Aw shucks, guys ... you make me blush with your compliments.",
    "time": 1314211127,
    "type": "comment",
}


@pytest.fixture
def conexao(tmp_path) -> sqlite3.Connection:
    """Banco SQLite novo, em arquivo temporário, com o schema criado."""
    conn = abrir(tmp_path / "teste.db")
    yield conn
    conn.close()


class ClienteFalso:
    """Dublê do cliente HTTP: devolve o que foi combinado, sem rede.

    Cada entrada de `respostas` é um dict (item), `None` (resposta null da API)
    ou uma instância de `ErroAPI` (falha depois dos retries).
    """

    def __init__(self, respostas: dict, maxitem: int = 0) -> None:
        self._respostas = respostas
        self._maxitem = maxitem
        self.consultados: list[int] = []

    def maxitem(self) -> int:
        return self._maxitem

    def item(self, identificador: int):
        self.consultados.append(identificador)
        resposta = self._respostas.get(identificador)
        if isinstance(resposta, ErroAPI):
            raise resposta
        return resposta
