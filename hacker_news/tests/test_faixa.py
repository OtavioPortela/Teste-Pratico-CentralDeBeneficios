"""Testes do cálculo da faixa: é ele que separa carga inicial de incremental."""

from src.carga import calcular_faixa


def test_carga_inicial_pega_os_ultimos_ids():
    faixa = calcular_faixa(watermark=None, maxitem=1000, limite_inicial=100)

    assert (faixa.inicio, faixa.fim) == (901, 1000)
    assert faixa.tipo == "inicial"
    assert faixa.quantidade == 100
    assert not faixa.vazia


def test_carga_inicial_com_maxitem_menor_que_o_limite():
    # Não pode gerar ID zero ou negativo.
    faixa = calcular_faixa(watermark=None, maxitem=40, limite_inicial=100)

    assert (faixa.inicio, faixa.fim) == (1, 40)
    assert faixa.quantidade == 40


def test_carga_incremental_comeca_no_id_seguinte_ao_watermark():
    faixa = calcular_faixa(watermark=1000, maxitem=1020, limite_inicial=100)

    assert (faixa.inicio, faixa.fim) == (1001, 1020)
    assert faixa.tipo == "incremental"
    assert faixa.quantidade == 20


def test_sem_itens_novos_gera_faixa_vazia():
    faixa = calcular_faixa(watermark=1000, maxitem=1000, limite_inicial=100)

    assert faixa.vazia
    assert faixa.quantidade == 0


def test_watermark_acima_do_maxitem_nao_processa_nada():
    # Cenário defensivo: maxitem "andou para trás" entre execuções.
    faixa = calcular_faixa(watermark=1005, maxitem=1000, limite_inicial=100)

    assert faixa.vazia
    assert faixa.quantidade == 0


def test_limite_inicial_menor_muda_apenas_a_carga_inicial():
    faixa = calcular_faixa(watermark=None, maxitem=1000, limite_inicial=10)

    assert (faixa.inicio, faixa.fim) == (991, 1000)
