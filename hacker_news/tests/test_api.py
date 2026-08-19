"""Testes do cliente HTTP: retries, backoff, null e erros definitivos.

Nenhum teste toca a rede: a `requests.Session` do cliente é substituída por um
dublê, e o backoff é neutralizado para a suíte não gastar tempo dormindo.
"""

import pytest
import requests

from src.api import ClienteHackerNews
from src.config import Config
from src.erros import ErroAPI


class RespostaFalsa:
    def __init__(self, corpo=None, status_code=200):
        self._corpo = corpo
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        if isinstance(self._corpo, Exception):
            raise self._corpo
        return self._corpo


class SessaoFalsa:
    """Devolve, em ordem, cada resposta combinada; exceções são levantadas."""

    def __init__(self, *respostas):
        self._respostas = list(respostas)
        self.chamadas: list[tuple[str, float]] = []

    def get(self, url, timeout=None):
        self.chamadas.append((url, timeout))
        proxima = self._respostas.pop(0)
        if isinstance(proxima, Exception):
            raise proxima
        return proxima

    def close(self):
        pass


@pytest.fixture
def esperas(monkeypatch) -> list[float]:
    """Captura os backoffs em vez de realmente dormir."""
    registradas: list[float] = []
    monkeypatch.setattr("src.api.time.sleep", registradas.append)
    return registradas


def montar(sessao, **kwargs) -> ClienteHackerNews:
    cliente = ClienteHackerNews(Config(**kwargs))
    cliente._sessao = sessao
    return cliente


def test_maxitem_devolve_inteiro(esperas):
    cliente = montar(SessaoFalsa(RespostaFalsa(49359648)))

    assert cliente.maxitem() == 49359648
    assert esperas == []


def test_item_devolve_o_payload(esperas):
    payload = {"id": 8863, "type": "story"}
    cliente = montar(SessaoFalsa(RespostaFalsa(payload)))

    assert cliente.item(8863) == payload


def test_resposta_null_devolve_none_sem_erro(esperas):
    # Null é resultado legítimo da API, não falha técnica.
    cliente = montar(SessaoFalsa(RespostaFalsa(None)))

    assert cliente.item(999) is None
    assert esperas == []


def test_todo_get_leva_timeout(esperas):
    sessao = SessaoFalsa(RespostaFalsa(1))
    cliente = montar(sessao, timeout=7.5)

    cliente.maxitem()

    assert sessao.chamadas[0][1] == 7.5


def test_timeout_seguido_de_sucesso_nao_falha(esperas):
    sessao = SessaoFalsa(requests.Timeout("demorou"), RespostaFalsa({"id": 10}))
    cliente = montar(sessao)

    assert cliente.item(10) == {"id": 10}
    assert len(sessao.chamadas) == 2
    assert esperas == [0.5]  # um backoff antes da segunda tentativa


def test_erro_de_conexao_seguido_de_sucesso(esperas):
    sessao = SessaoFalsa(requests.ConnectionError("recusada"), RespostaFalsa({"id": 11}))
    cliente = montar(sessao)

    assert cliente.item(11) == {"id": 11}


def test_status_transitorio_e_repetido(esperas):
    sessao = SessaoFalsa(RespostaFalsa(status_code=503), RespostaFalsa({"id": 12}))
    cliente = montar(sessao)

    assert cliente.item(12) == {"id": 12}
    assert len(sessao.chamadas) == 2


def test_falha_definitiva_apos_esgotar_as_tentativas(esperas):
    sessao = SessaoFalsa(*[requests.Timeout("demorou")] * 3)
    cliente = montar(sessao, tentativas=3)

    with pytest.raises(ErroAPI, match="timeout após 3 tentativas"):
        cliente.item(13)

    assert len(sessao.chamadas) == 3
    assert esperas == [0.5, 1.0]  # backoff crescente, sem espera após a última


def test_erro_http_definitivo_nao_e_repetido(esperas):
    sessao = SessaoFalsa(RespostaFalsa(status_code=404), RespostaFalsa({"id": 14}))
    cliente = montar(sessao)

    with pytest.raises(ErroAPI, match="HTTP 404"):
        cliente.item(14)

    assert len(sessao.chamadas) == 1  # não insistiu no que não iria mudar


def test_corpo_ilegivel_e_tratado_como_transitorio(esperas):
    sessao = SessaoFalsa(
        RespostaFalsa(ValueError("json quebrado")), RespostaFalsa({"id": 15})
    )
    cliente = montar(sessao)

    assert cliente.item(15) == {"id": 15}


def test_maxitem_em_formato_inesperado(esperas):
    cliente = montar(SessaoFalsa(RespostaFalsa("quarenta")))

    with pytest.raises(ErroAPI, match="maxitem inválido"):
        cliente.maxitem()


def test_item_em_formato_inesperado(esperas):
    cliente = montar(SessaoFalsa(RespostaFalsa([1, 2, 3])))

    with pytest.raises(ErroAPI, match="formato inesperado"):
        cliente.item(16)
