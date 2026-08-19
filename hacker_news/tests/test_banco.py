"""Testes da persistência: schema, campos, raw_json, unicidade e estado."""

import json
import sqlite3

import pytest

from src.banco import (
    CHAVE_WATERMARK,
    abrir,
    gravar_watermark,
    ler_watermark,
    salvar_item,
)
from src.erros import ErroBanco
from tests.conftest import COMENTARIO, STORY


def test_banco_novo_cria_schema_completo(tmp_path):
    caminho = tmp_path / "novo.db"
    assert not caminho.exists()

    conexao = abrir(caminho)

    tabelas = {
        linha["name"]
        for linha in conexao.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    indices = {
        linha["name"]
        for linha in conexao.execute("SELECT name FROM sqlite_master WHERE type='index'")
    }
    assert {"items", "sync_state"} <= tabelas
    assert {"idx_items_type", "idx_items_time"} <= indices
    assert caminho.exists()
    conexao.close()


def test_abrir_banco_existente_nao_apaga_dados(tmp_path):
    caminho = tmp_path / "existente.db"
    primeira = abrir(caminho)
    with primeira:
        salvar_item(primeira, STORY)
    primeira.close()

    segunda = abrir(caminho)

    assert segunda.execute("SELECT COUNT(*) c FROM items").fetchone()["c"] == 1
    segunda.close()


def test_id_e_chave_primaria_no_schema(conexao):
    colunas = {
        linha["name"]: linha for linha in conexao.execute("PRAGMA table_info(items)")
    }
    assert colunas["id"]["pk"] == 1
    assert colunas["raw_json"]["notnull"] == 1


def test_banco_impede_id_duplicado_estruturalmente(conexao):
    # Insert cru, sem passar por salvar_item: quem barra é a constraint.
    conexao.execute(
        "INSERT INTO items (id, raw_json, fetched_at) VALUES (?, ?, ?)",
        (8863, "{}", "2026-01-01T00:00:00+00:00"),
    )

    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(
            "INSERT INTO items (id, raw_json, fetched_at) VALUES (?, ?, ?)",
            (8863, "{}", "2026-01-01T00:00:00+00:00"),
        )


def test_campos_consultaveis_vao_para_as_colunas(conexao):
    with conexao:
        assert salvar_item(conexao, STORY) == "inserido"

    linha = conexao.execute("SELECT * FROM items WHERE id = ?", (8863,)).fetchone()
    assert linha["type"] == "story"
    assert linha["author"] == "dhouston"  # o campo "by" da API
    assert linha["time"] == 1175714200
    assert linha["title"] == "My YC app: Dropbox - Throw away your USB drive"
    assert linha["url"].startswith("http://www.getdropbox.com")
    assert linha["score"] == 104
    assert linha["descendants"] == 71
    assert linha["parent"] is None
    assert linha["deleted"] is None and linha["dead"] is None


def test_campos_ausentes_de_um_comentario_ficam_nulos(conexao):
    with conexao:
        salvar_item(conexao, COMENTARIO)

    linha = conexao.execute("SELECT * FROM items WHERE id = ?", (2921983,)).fetchone()
    assert linha["type"] == "comment"
    assert linha["parent"] == 2921506
    assert linha["title"] is None and linha["url"] is None and linha["score"] is None


def test_flags_deleted_e_dead_viram_inteiros(conexao):
    with conexao:
        salvar_item(conexao, {"id": 1, "type": "comment", "dead": True, "deleted": True})

    linha = conexao.execute("SELECT * FROM items WHERE id = 1").fetchone()
    assert linha["dead"] == 1 and linha["deleted"] == 1


def test_raw_json_preserva_o_payload_inteiro(conexao):
    with conexao:
        salvar_item(conexao, STORY)

    bruto = conexao.execute(
        "SELECT raw_json FROM items WHERE id = ?", (8863,)
    ).fetchone()["raw_json"]
    # Inclusive o que não virou coluna, como a lista "kids".
    assert json.loads(bruto) == STORY


def test_salvar_o_mesmo_item_duas_vezes_nao_duplica(conexao):
    with conexao:
        primeira = salvar_item(conexao, STORY)
    with conexao:
        segunda = salvar_item(conexao, STORY)

    total = conexao.execute("SELECT COUNT(*) c, COUNT(DISTINCT id) d FROM items").fetchone()
    assert (primeira, segunda) == ("inserido", "atualizado")
    assert total["c"] == total["d"] == 1


def test_reprocessar_item_atualiza_os_campos(conexao):
    with conexao:
        salvar_item(conexao, STORY)
    with conexao:
        salvar_item(conexao, {**STORY, "score": 999})

    linha = conexao.execute("SELECT score FROM items WHERE id = ?", (8863,)).fetchone()
    assert linha["score"] == 999


def test_item_sem_id_falha_explicitamente(conexao):
    with pytest.raises(ErroBanco, match="sem id utilizável"):
        salvar_item(conexao, {"type": "story"})


def test_estado_inexistente_devolve_none(conexao):
    assert ler_watermark(conexao) is None


def test_estado_gravado_e_lido(conexao):
    with conexao:
        gravar_watermark(conexao, 1000)

    assert ler_watermark(conexao) == 1000


def test_estado_e_atualizado_sem_duplicar_a_chave(conexao):
    with conexao:
        gravar_watermark(conexao, 1000)
    with conexao:
        gravar_watermark(conexao, 1020)

    total = conexao.execute(
        "SELECT COUNT(*) c FROM sync_state WHERE chave = ?", (CHAVE_WATERMARK,)
    ).fetchone()["c"]
    assert ler_watermark(conexao) == 1020
    assert total == 1
