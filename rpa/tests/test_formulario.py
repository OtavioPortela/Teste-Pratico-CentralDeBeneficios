"""Testes do vocabulário usado para identificar os campos na tela."""

import pytest

from src.formulario import ROTULOS, normalizar_rotulo
from src.planilha import COLUNAS


@pytest.mark.parametrize(
    "rotulo, campo",
    [
        ("First Name", "first_name"),
        ("Role in Company", "role_in_company"),
        ("  phone   number ", "phone_number"),
        ("PHONE NUMBER", "phone_number"),
    ],
)
def test_rotulo_da_tela_mapeia_para_o_campo(rotulo, campo):
    assert ROTULOS[normalizar_rotulo(rotulo)] == campo


def test_rotulo_desconhecido_nao_tem_campo():
    assert normalizar_rotulo("Nickname") not in ROTULOS


def test_tela_e_planilha_cobrem_os_mesmos_campos():
    # Um campo lido da planilha sem destino na tela (ou vice-versa) deixaria
    # o preenchimento incompleto e derrubaria a acurácia.
    assert set(ROTULOS.values()) == set(COLUNAS.values())
