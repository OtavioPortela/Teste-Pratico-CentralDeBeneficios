"""Testes do coração do pipeline: null, falha conservadora e watermark."""

import json

import pytest

from src.banco import ler_watermark
from src.carga import Faixa, executar, processar
from src.config import Config
from src.erros import ErroAPI
from tests.conftest import STORY, ClienteFalso


def item(identificador: int, **extras) -> dict:
    return {"id": identificador, "type": "comment", "by": "alguem", **extras}


def test_faixa_processada_por_inteiro(conexao):
    cliente = ClienteFalso({101: item(101), 102: item(102), 103: item(103)})

    resumo = processar(cliente, conexao, Faixa(101, 103, "incremental"), 100)

    assert (resumo.consultados, resumo.inseridos, resumo.falhas) == (3, 3, 0)
    assert resumo.watermark_final == 103
    assert ler_watermark(conexao) == 103
    assert cliente.consultados == [101, 102, 103]


def test_null_e_ignorado_e_o_watermark_avanca(conexao):
    # A API respondeu normalmente com null: o ID está processado, não falhou.
    cliente = ClienteFalso({101: item(101), 102: None, 103: item(103)})

    resumo = processar(cliente, conexao, Faixa(101, 103, "incremental"), 100)

    assert (resumo.ignorados, resumo.inseridos, resumo.falhas) == (1, 2, 0)
    assert resumo.consultados == 3
    assert not resumo.interrompida
    assert resumo.watermark_final == 103  # passou por cima do null
    assert ler_watermark(conexao) == 103
    assert cliente.consultados == [101, 102, 103]  # não parou no null


def test_falha_definitiva_interrompe_e_segura_o_watermark(conexao):
    cliente = ClienteFalso(
        {
            101: item(101),
            102: item(102),
            103: ErroAPI("timeout após 3 tentativas"),
            104: item(104),
            105: item(105),
        }
    )

    resumo = processar(cliente, conexao, Faixa(101, 105, "incremental"), 100)

    assert resumo.interrompida
    assert (resumo.falhas, resumo.id_falha) == (1, 103)
    assert resumo.inseridos == 2
    assert resumo.consultados == 3  # o ID que falhou conta como consultado
    assert resumo.watermark_final == 102  # não ultrapassa o ID que falhou
    assert ler_watermark(conexao) == 102
    assert cliente.consultados == [101, 102, 103]  # 104 e 105 não foram tocados
    assert conexao.execute("SELECT COUNT(*) c FROM items").fetchone()["c"] == 2


def test_falha_no_primeiro_id_mantem_o_watermark_anterior(conexao):
    cliente = ClienteFalso({101: ErroAPI("erro de conexão após 3 tentativas")})

    resumo = processar(cliente, conexao, Faixa(101, 105, "incremental"), 100)

    assert resumo.watermark_final == 100
    assert resumo.inseridos == 0
    assert ler_watermark(conexao) is None  # nada foi processado, nada foi gravado


def test_retomada_comeca_no_id_que_falhou(conexao):
    falha = ClienteFalso({101: item(101), 102: ErroAPI("timeout")})
    processar(falha, conexao, Faixa(101, 103, "incremental"), 100)

    # Execução seguinte, com a API respondendo: parte do 102, não do 103.
    retomada = ClienteFalso({102: item(102), 103: item(103)})
    resumo = processar(retomada, conexao, Faixa(102, 103, "incremental"), 101)

    assert retomada.consultados == [102, 103]
    assert resumo.inseridos == 2
    assert ler_watermark(conexao) == 103


def test_faixa_vazia_nao_consulta_nada(conexao):
    cliente = ClienteFalso({})

    resumo = processar(cliente, conexao, Faixa(101, 100, "incremental"), 100)

    assert (resumo.consultados, resumo.inseridos, resumo.falhas) == (0, 0, 0)
    assert cliente.consultados == []
    assert resumo.watermark_final == 100


def test_reprocessar_a_mesma_faixa_nao_duplica(conexao):
    faixa = Faixa(101, 103, "incremental")
    respostas = {101: item(101), 102: item(102), 103: item(103)}

    primeira = processar(ClienteFalso(respostas), conexao, faixa, 100)
    segunda = processar(ClienteFalso(respostas), conexao, faixa, 100)

    total = conexao.execute(
        "SELECT COUNT(*) c, COUNT(DISTINCT id) d FROM items"
    ).fetchone()
    assert (primeira.inseridos, primeira.atualizados) == (3, 0)
    assert (segunda.inseridos, segunda.atualizados) == (0, 3)
    assert total["c"] == total["d"] == 3


def test_raw_json_do_item_persistido_pelo_pipeline(conexao):
    cliente = ClienteFalso({8863: STORY})

    processar(cliente, conexao, Faixa(8863, 8863, "incremental"), 8862)

    bruto = conexao.execute(
        "SELECT raw_json FROM items WHERE id = ?", (8863,)
    ).fetchone()["raw_json"]
    assert json.loads(bruto) == STORY


@pytest.fixture
def config_temporaria(tmp_path) -> Config:
    return Config(banco=tmp_path / "hn.db", dir_artifacts=tmp_path / "artifacts")


def _fixar_cliente(monkeypatch, cliente) -> None:
    """Troca o cliente HTTP real por um dublê, sem tocar na rede."""
    monkeypatch.setattr("src.carga.ClienteHackerNews", lambda _config: cliente)


class ClienteContexto(ClienteFalso):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


def test_primeira_execucao_faz_carga_inicial_limitada(monkeypatch, config_temporaria):
    respostas = {identificador: item(identificador) for identificador in range(991, 1001)}
    cliente = ClienteContexto(respostas, maxitem=1000)
    _fixar_cliente(monkeypatch, cliente)

    resumo = executar(Config(**{**vars(config_temporaria), "limite_inicial": 10}))

    assert resumo.tipo == "inicial"
    assert (resumo.faixa_inicio, resumo.faixa_fim) == (991, 1000)
    assert resumo.inseridos == 10
    assert resumo.watermark_inicial is None and resumo.watermark_final == 1000
    assert (config_temporaria.dir_artifacts / "resumo.json").is_file()


def test_segunda_execucao_consulta_apenas_o_intervalo_novo(monkeypatch, config_temporaria):
    config = Config(**{**vars(config_temporaria), "limite_inicial": 10})
    inicial = ClienteContexto(
        {i: item(i) for i in range(991, 1001)}, maxitem=1000
    )
    _fixar_cliente(monkeypatch, inicial)
    executar(config)

    incremental = ClienteContexto({i: item(i) for i in range(1001, 1004)}, maxitem=1003)
    _fixar_cliente(monkeypatch, incremental)
    resumo = executar(config)

    assert resumo.tipo == "incremental"
    assert incremental.consultados == [1001, 1002, 1003]  # não voltou aos 10 iniciais
    assert resumo.consultados == 3
    assert resumo.watermark_inicial == 1000 and resumo.watermark_final == 1003


def test_execucao_sem_itens_novos_e_bem_sucedida(monkeypatch, config_temporaria):
    config = Config(**{**vars(config_temporaria), "limite_inicial": 10})
    _fixar_cliente(monkeypatch, ClienteContexto({i: item(i) for i in range(991, 1001)}, 1000))
    executar(config)

    parado = ClienteContexto({}, maxitem=1000)
    _fixar_cliente(monkeypatch, parado)
    resumo = executar(config)

    assert resumo.vazia and not resumo.interrompida
    assert (resumo.consultados, resumo.inseridos, resumo.falhas) == (0, 0, 0)
    assert parado.consultados == []
    assert resumo.watermark_final == 1000
