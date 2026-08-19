"""Testes do relatório: as métricas que o PDF exige precisam bater."""

import json

from src.resultado import Resumo, formatar, salvar_json


def resumo_completo(**extras) -> Resumo:
    padrao = dict(
        tipo="incremental",
        faixa_inicio=500001,
        faixa_fim=500025,
        consultados=25,
        inseridos=23,
        atualizados=0,
        ignorados=2,
        falhas=0,
        watermark_inicial=500000,
        watermark_final=500025,
        duracao_s=2.84,
    )
    return Resumo(**{**padrao, **extras})


def test_relatorio_de_sucesso_traz_todas_as_metricas_do_pdf():
    texto = formatar(resumo_completo())

    for esperado in (
        "Carga incremental concluída",
        "Tipo: incremental",
        "Faixa: 500001 → 500025",
        "Consultados: 25",
        "Inseridos: 23",
        "Atualizados: 0",
        "Ignorados: 2",
        "Falhas: 0",
        "Watermark inicial: 500000",
        "Watermark final: 500025",
        "Duração: 2.84 s",
    ):
        assert esperado in texto


def test_relatorio_de_interrupcao_mostra_o_id_com_falha():
    texto = formatar(
        resumo_completo(
            consultados=13,
            inseridos=12,
            ignorados=0,
            falhas=1,
            id_falha=500013,
            watermark_final=500012,
            interrompida=True,
            erro="timeout após 3 tentativas",
        )
    )

    assert "Carga interrompida" in texto
    assert "Faixa planejada: 500001 → 500025" in texto
    assert "Último processado: 500012" in texto
    assert "ID com falha: 500013" in texto
    assert "Watermark final: 500012" in texto
    assert "timeout após 3 tentativas" in texto


def test_relatorio_sem_itens_novos():
    vazio = Resumo(
        tipo="incremental",
        faixa_inicio=1001,
        faixa_fim=1000,
        watermark_inicial=1000,
        watermark_final=1000,
    )

    texto = formatar(vazio)

    assert vazio.vazia
    assert "Nenhum item novo para processar." in texto
    assert "Consultados: 0" in texto
    assert "Falhas: 0" in texto


def test_carga_inicial_aparece_como_inicial():
    texto = formatar(resumo_completo(tipo="inicial", watermark_inicial=None))

    assert "Carga inicial concluída" in texto
    assert "Tipo: inicial" in texto
    assert "Watermark inicial: None" in texto


def test_resumo_salvo_em_json_preserva_as_metricas(tmp_path):
    destino = salvar_json(tmp_path / "resumo.json", resumo_completo())

    conteudo = json.loads(destino.read_text(encoding="utf-8"))
    assert conteudo["consultados"] == 25
    assert conteudo["inseridos"] == 23
    assert conteudo["ignorados"] == 2
    assert conteudo["watermark_final"] == 500025
    assert conteudo["interrompida"] is False
