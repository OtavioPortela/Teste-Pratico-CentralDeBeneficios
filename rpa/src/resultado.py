"""Interpretação da mensagem final do desafio e registro das evidências."""

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .erros import ErroResultado

logger = logging.getLogger(__name__)

# "Your success rate is 100% ( 70 out of 70 fields) in 69340 milliseconds"
PADRAO = re.compile(
    r"(?P<acuracia>\d+)\s*%.*?"
    r"(?P<preenchidos>\d+)\s+out of\s+(?P<total>\d+)\s+fields.*?"
    r"in\s+(?P<duracao>\d+)\s+milliseconds",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class Resultado:
    """Números informados pelo próprio site ao final do desafio."""

    mensagem: str
    acuracia_percentual: int
    campos_preenchidos: int
    campos_totais: int
    duracao_desafio_ms: int


def interpretar_mensagem(mensagem: str) -> Resultado:
    """Extrai acurácia, campos e duração da mensagem exibida pelo site."""
    encontrado = PADRAO.search(mensagem)
    if not encontrado:
        raise ErroResultado(f"mensagem de resultado em formato inesperado: {mensagem!r}")
    return Resultado(
        mensagem=" ".join(mensagem.split()),
        acuracia_percentual=int(encontrado["acuracia"]),
        campos_preenchidos=int(encontrado["preenchidos"]),
        campos_totais=int(encontrado["total"]),
        duracao_desafio_ms=int(encontrado["duracao"]),
    )


def salvar_json(destino: Path, resultado: Resultado, execucao: dict) -> Path:
    """Grava o resultado estruturado da execução em artifacts/."""
    conteudo = {**execucao, "resultado": asdict(resultado)}
    destino.write_text(
        json.dumps(conteudo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    logger.info("Resultado salvo em %s", destino.name)
    return destino
