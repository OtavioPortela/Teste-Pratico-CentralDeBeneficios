"""Métricas da execução e o relatório operacional."""

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Resumo:
    """Contabilidade de uma execução da carga."""

    tipo: str
    faixa_inicio: int | None = None
    faixa_fim: int | None = None
    consultados: int = 0
    inseridos: int = 0
    atualizados: int = 0
    ignorados: int = 0
    falhas: int = 0
    watermark_inicial: int | None = None
    watermark_final: int | None = None
    id_falha: int | None = None
    interrompida: bool = False
    duracao_s: float = 0.0
    erro: str | None = field(default=None)

    @property
    def vazia(self) -> bool:
        """Nada a fazer: não havia ID novo no intervalo."""
        return self.faixa_inicio is None or self.faixa_inicio > (self.faixa_fim or 0)


def formatar(resumo: Resumo) -> str:
    """Monta o relatório que vai para o terminal e para os artifacts."""
    if resumo.vazia and not resumo.interrompida:
        return (
            "Nenhum item novo para processar.\n"
            f"Tipo: {resumo.tipo}\n"
            f"Consultados: 0\n"
            f"Inseridos: 0\n"
            f"Falhas: 0\n"
            f"Watermark: {resumo.watermark_final}\n"
            f"Duração: {resumo.duracao_s:.2f} s"
        )

    faixa = f"{resumo.faixa_inicio} → {resumo.faixa_fim}"
    if resumo.interrompida:
        linhas = [
            "Carga interrompida",
            "",
            f"Tipo: {resumo.tipo}",
            f"Faixa planejada: {faixa}",
            f"Último processado: {resumo.watermark_final}",
            f"ID com falha: {resumo.id_falha}",
        ]
    else:
        linhas = [
            f"Carga {resumo.tipo} concluída",
            "",
            f"Tipo: {resumo.tipo}",
            f"Faixa: {faixa}",
        ]

    linhas += [
        f"Consultados: {resumo.consultados}",
        f"Inseridos: {resumo.inseridos}",
        f"Atualizados: {resumo.atualizados}",
        f"Ignorados: {resumo.ignorados}",
        f"Falhas: {resumo.falhas}",
        f"Watermark inicial: {resumo.watermark_inicial}",
        f"Watermark final: {resumo.watermark_final}",
        f"Duração: {resumo.duracao_s:.2f} s",
    ]
    if resumo.erro:
        linhas.append(f"Motivo da falha: {resumo.erro}")
    return "\n".join(linhas)


def salvar_json(destino: Path, resumo: Resumo) -> Path:
    """Grava o resumo estruturado da execução como evidência."""
    conteudo = asdict(resumo)
    destino.write_text(
        json.dumps(conteudo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    logger.info("Resumo salvo em %s", destino.name)
    return destino
