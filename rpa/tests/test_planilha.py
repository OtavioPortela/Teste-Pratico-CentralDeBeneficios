"""Testes da leitura da planilha: normalização, validação e conversão."""

import pytest
from openpyxl import Workbook

from src.erros import ErroPlanilha
from src.planilha import (
    Registro,
    ler_registros,
    normalizar_cabecalho,
    normalizar_valor,
)

CABECALHO_OFICIAL = [
    "First Name",
    "Last Name ",  # a planilha do desafio traz espaço à direita
    "Company Name",
    "Role in Company",
    "Address",
    "Email",
    "Phone Number",
]

LINHA_OFICIAL = [
    "John",
    "Smith",
    "IT Solutions",
    "Analyst",
    "98 North Road",
    "jsmith@itsolutions.co.uk",
    40716543298,  # o telefone vem como inteiro
]


def criar_planilha(tmp_path, cabecalho, linhas):
    arquivo = tmp_path / "challenge.xlsx"
    planilha = Workbook()
    aba = planilha.active
    aba.append(cabecalho)
    for linha in linhas:
        aba.append(linha)
    planilha.save(arquivo)
    return arquivo


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("Last Name ", "last name"),
        ("  First   Name ", "first name"),
        ("PHONE NUMBER", "phone number"),
        (None, ""),
    ],
)
def test_normalizar_cabecalho(entrada, esperado):
    assert normalizar_cabecalho(entrada) == esperado


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        (40716543298, "40716543298"),  # inteiro não pode virar notação científica
        (40716543298.0, "40716543298"),  # float inteiro não pode manter o ".0"
        ("  IT Solutions  ", "IT Solutions"),
        (None, ""),
    ],
)
def test_normalizar_valor(entrada, esperado):
    assert normalizar_valor(entrada) == esperado


def test_ler_registros_da_planilha_oficial(tmp_path):
    arquivo = criar_planilha(tmp_path, CABECALHO_OFICIAL, [LINHA_OFICIAL])

    registros = ler_registros(arquivo)

    assert registros == [
        Registro(
            first_name="John",
            last_name="Smith",
            company_name="IT Solutions",
            role_in_company="Analyst",
            address="98 North Road",
            email="jsmith@itsolutions.co.uk",
            phone_number="40716543298",
        )
    ]


def test_ordem_das_colunas_nao_importa(tmp_path):
    invertido = list(reversed(CABECALHO_OFICIAL))
    arquivo = criar_planilha(tmp_path, invertido, [list(reversed(LINHA_OFICIAL))])

    registro = ler_registros(arquivo)[0]

    assert registro.first_name == "John"
    assert registro.phone_number == "40716543298"


def test_linhas_em_branco_sao_ignoradas(tmp_path):
    # A planilha oficial declara mil linhas, quase todas vazias.
    linhas = [LINHA_OFICIAL, [None] * 7, ["", "", "", "", "", "", ""]]
    arquivo = criar_planilha(tmp_path, CABECALHO_OFICIAL, linhas)

    assert len(ler_registros(arquivo)) == 1


def test_coluna_obrigatoria_ausente(tmp_path):
    sem_email = [c for c in CABECALHO_OFICIAL if c != "Email"]
    arquivo = criar_planilha(tmp_path, sem_email, [LINHA_OFICIAL[:5] + LINHA_OFICIAL[6:]])

    with pytest.raises(ErroPlanilha, match="email"):
        ler_registros(arquivo)


def test_registro_com_campo_vazio_falha(tmp_path):
    incompleta = ["John", None, "IT Solutions", "Analyst", "98 North Road", "j@x.com", 1]
    arquivo = criar_planilha(tmp_path, CABECALHO_OFICIAL, [incompleta])

    with pytest.raises(ErroPlanilha, match="linha 2"):
        ler_registros(arquivo)


def test_planilha_inexistente(tmp_path):
    with pytest.raises(ErroPlanilha, match="não encontrada"):
        ler_registros(tmp_path / "nao_existe.xlsx")


def test_planilha_sem_registros(tmp_path):
    arquivo = criar_planilha(tmp_path, CABECALHO_OFICIAL, [])

    with pytest.raises(ErroPlanilha, match="não contém registros"):
        ler_registros(arquivo)
