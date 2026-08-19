"""Testes da leitura da mensagem final exibida pelo desafio."""

import pytest

from src.erros import ErroResultado
from src.resultado import interpretar_mensagem

MENSAGEM_REAL = "Your success rate is 100% ( 70 out of 70 fields) in 69340 milliseconds"


def test_interpretar_mensagem_de_sucesso():
    resultado = interpretar_mensagem(MENSAGEM_REAL)

    assert resultado.acuracia_percentual == 100
    assert resultado.campos_preenchidos == 70
    assert resultado.campos_totais == 70
    assert resultado.duracao_desafio_ms == 69340


def test_interpretar_mensagem_parcial():
    resultado = interpretar_mensagem(
        "Your success rate is 90% ( 63 out of 70 fields) in 51200 milliseconds"
    )

    assert resultado.acuracia_percentual == 90
    assert resultado.campos_preenchidos == 63


@pytest.mark.parametrize("mensagem", ["", "Congratulations!", "success rate is 100%"])
def test_mensagem_em_formato_inesperado(mensagem):
    with pytest.raises(ErroResultado, match="formato inesperado"):
        interpretar_mensagem(mensagem)
