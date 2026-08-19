"""Persistência local em SQLite.

Sabe gravar itens e guardar o estado da carga; não faz requisição HTTP nem
decide faixas. O banco, as tabelas e os índices são criados na abertura, para
que o projeto rode em máquina limpa sem preparação manual.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .erros import ErroBanco

logger = logging.getLogger(__name__)

CHAVE_WATERMARK = "last_item_id"

# `id` é a identidade natural do Hacker News: como chave primária, o próprio
# banco impede duplicidade, sem depender de uma checagem prévia no código.
SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY,
    type        TEXT,
    author      TEXT,
    time        INTEGER,
    title       TEXT,
    url         TEXT,
    score       INTEGER,
    parent      INTEGER,
    descendants INTEGER,
    deleted     INTEGER,
    dead        INTEGER,
    raw_json    TEXT NOT NULL,
    fetched_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_type ON items(type);
CREATE INDEX IF NOT EXISTS idx_items_time ON items(time);

CREATE TABLE IF NOT EXISTS sync_state (
    chave         TEXT PRIMARY KEY,
    valor         INTEGER NOT NULL,
    atualizado_em TEXT NOT NULL
);
"""

INSERIR_ITEM = """
INSERT INTO items (
    id, type, author, time, title, url, score,
    parent, descendants, deleted, dead, raw_json, fetched_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    type        = excluded.type,
    author      = excluded.author,
    time        = excluded.time,
    title       = excluded.title,
    url         = excluded.url,
    score       = excluded.score,
    parent      = excluded.parent,
    descendants = excluded.descendants,
    deleted     = excluded.deleted,
    dead        = excluded.dead,
    raw_json    = excluded.raw_json,
    fetched_at  = excluded.fetched_at
"""


def abrir(caminho: Path) -> sqlite3.Connection:
    """Abre (criando se necessário) o banco e garante o schema."""
    novo = not caminho.exists()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    try:
        conexao = sqlite3.connect(caminho)
        conexao.row_factory = sqlite3.Row
        conexao.executescript(SCHEMA)
        conexao.commit()
    except sqlite3.Error as erro:
        raise ErroBanco(f"não foi possível abrir o banco {caminho}: {erro}") from erro

    logger.info("Banco %s (%s)", caminho, "criado" if novo else "existente")
    return conexao


def _booleano(valor: Any) -> int | None:
    """Converte as flags `deleted`/`dead` da API em 0/1, preservando ausência."""
    return None if valor is None else int(bool(valor))


def salvar_item(conexao: sqlite3.Connection, item: dict[str, Any]) -> str:
    """Grava o item e devolve "inserido" ou "atualizado".

    A consulta prévia serve apenas para classificar a métrica; quem impede
    duplicidade é a chave primária, junto do ON CONFLICT do próprio INSERT.
    """
    identificador = item.get("id")
    if not isinstance(identificador, int):
        raise ErroBanco(f"item sem id utilizável: {item!r}")

    existente = conexao.execute(
        "SELECT 1 FROM items WHERE id = ?", (identificador,)
    ).fetchone()

    valores = (
        identificador,
        item.get("type"),
        item.get("by"),
        item.get("time"),
        item.get("title"),
        item.get("url"),
        item.get("score"),
        item.get("parent"),
        item.get("descendants"),
        _booleano(item.get("deleted")),
        _booleano(item.get("dead")),
        json.dumps(item, ensure_ascii=False, sort_keys=True),
        datetime.now(timezone.utc).isoformat(),
    )
    try:
        conexao.execute(INSERIR_ITEM, valores)
    except sqlite3.Error as erro:
        raise ErroBanco(f"falha ao gravar o item {identificador}: {erro}") from erro

    return "atualizado" if existente else "inserido"


def ler_watermark(conexao: sqlite3.Connection) -> int | None:
    """Último ID processado com sucesso, ou `None` se a carga nunca rodou."""
    try:
        linha = conexao.execute(
            "SELECT valor FROM sync_state WHERE chave = ?", (CHAVE_WATERMARK,)
        ).fetchone()
    except sqlite3.Error as erro:
        raise ErroBanco(f"falha ao ler o estado da carga: {erro}") from erro
    return linha["valor"] if linha else None


def gravar_watermark(conexao: sqlite3.Connection, valor: int) -> None:
    """Registra o último ID processado com sucesso."""
    try:
        conexao.execute(
            """
            INSERT INTO sync_state (chave, valor, atualizado_em) VALUES (?, ?, ?)
            ON CONFLICT(chave) DO UPDATE SET
                valor = excluded.valor,
                atualizado_em = excluded.atualizado_em
            """,
            (CHAVE_WATERMARK, valor, datetime.now(timezone.utc).isoformat()),
        )
    except sqlite3.Error as erro:
        raise ErroBanco(f"falha ao gravar o estado da carga: {erro}") from erro
