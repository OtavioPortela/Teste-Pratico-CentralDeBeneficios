"""Orquestração da carga: decide a faixa, processa os IDs e move o watermark.

O processamento é sequencial e crescente. O watermark só avança depois que o
ID atual foi efetivamente processado — persistido ou classificado como
ignorado — e a persistência do item anda junto com a atualização do estado, na
mesma transação. Falha definitiva em um ID interrompe a execução ali: é
preferível parar a deixar um buraco silencioso no intervalo.
"""

import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from .api import ClienteHackerNews
from .banco import abrir, gravar_watermark, ler_watermark, salvar_item
from .config import Config
from .erros import ErroAPI
from .resultado import Resumo, salvar_json

logger = logging.getLogger(__name__)

INTERVALO_PROGRESSO = 25


@dataclass(frozen=True)
class Faixa:
    """Intervalo fechado de IDs a processar nesta execução."""

    inicio: int
    fim: int
    tipo: str

    @property
    def vazia(self) -> bool:
        return self.inicio > self.fim

    @property
    def quantidade(self) -> int:
        return 0 if self.vazia else self.fim - self.inicio + 1


def calcular_faixa(
    watermark: int | None, maxitem: int, limite_inicial: int
) -> Faixa:
    """Define o que processar: os últimos N IDs, ou só o que veio depois."""
    if watermark is None:
        inicio = max(1, maxitem - limite_inicial + 1)
        return Faixa(inicio, maxitem, "inicial")
    return Faixa(watermark + 1, maxitem, "incremental")


def processar(
    cliente: ClienteHackerNews,
    conexao: sqlite3.Connection,
    faixa: Faixa,
    watermark_inicial: int | None,
) -> Resumo:
    """Percorre a faixa em ordem crescente, item a item."""
    resumo = Resumo(
        tipo=faixa.tipo,
        faixa_inicio=faixa.inicio,
        faixa_fim=faixa.fim,
        watermark_inicial=watermark_inicial,
        watermark_final=watermark_inicial,
    )

    for identificador in range(faixa.inicio, faixa.fim + 1):
        resumo.consultados += 1
        try:
            item = cliente.item(identificador)
        except ErroAPI as erro:
            resumo.falhas += 1
            resumo.id_falha = identificador
            resumo.interrompida = True
            resumo.erro = str(erro)
            logger.error(
                "Item %d falhou definitivamente (%s); execução interrompida com "
                "watermark em %s",
                identificador,
                erro,
                resumo.watermark_final,
            )
            break

        # Item e watermark na mesma transação: ou os dois avançam, ou nenhum.
        with conexao:
            if item is None:
                resumo.ignorados += 1
                logger.info("Item %d: resposta null, ignorado", identificador)
            else:
                situacao = salvar_item(conexao, item)
                if situacao == "inserido":
                    resumo.inseridos += 1
                else:
                    resumo.atualizados += 1
                    logger.info("Item %d já existia, registro atualizado", identificador)
                logger.debug("Item %d %s (%s)", identificador, situacao, item.get("type"))
            gravar_watermark(conexao, identificador)

        resumo.watermark_final = identificador
        if resumo.consultados % INTERVALO_PROGRESSO == 0:
            logger.info(
                "Progresso: %d de %d IDs processados (watermark %d)",
                resumo.consultados,
                faixa.quantidade,
                identificador,
            )

    return resumo


def executar(config: Config) -> Resumo:
    """Executa uma carga completa e devolve o resumo com as métricas."""
    config.preparar_diretorios()
    comeco = time.monotonic()
    logger.info("Iniciando carga em %s", datetime.now(timezone.utc).isoformat())

    conexao = abrir(config.banco)
    try:
        watermark = ler_watermark(conexao)
        logger.info(
            "Watermark inicial: %s",
            watermark if watermark is not None else "ausente (primeira execução)",
        )

        with ClienteHackerNews(config) as cliente:
            maxitem = cliente.maxitem()
            logger.info("maxitem atual: %d", maxitem)

            faixa = calcular_faixa(watermark, maxitem, config.limite_inicial)
            if faixa.vazia:
                logger.info("Nenhum item novo: watermark %s alcança o maxitem", watermark)
                resumo = Resumo(
                    tipo=faixa.tipo,
                    faixa_inicio=faixa.inicio,
                    faixa_fim=faixa.fim,
                    watermark_inicial=watermark,
                    watermark_final=watermark,
                )
            else:
                logger.info(
                    "Carga %s: faixa %d → %d (%d IDs)",
                    faixa.tipo,
                    faixa.inicio,
                    faixa.fim,
                    faixa.quantidade,
                )
                resumo = processar(cliente, conexao, faixa, watermark)
    finally:
        conexao.close()

    resumo.duracao_s = round(time.monotonic() - comeco, 2)
    salvar_json(config.dir_artifacts / "resumo.json", resumo)
    return resumo
