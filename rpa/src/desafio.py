"""Orquestração do desafio: navegador, planilha, formulário e evidências."""

import logging
from datetime import datetime, timezone

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from .config import Config
from .download import baixar_planilha
from .erros import ErroFormulario
from .formulario import (
    aguardar_novo_formulario,
    aguardar_pagina,
    capturar_resultado,
    iniciar_desafio,
    mapear_campos,
    preencher,
    rodada_atual,
    submeter,
)
from .navegador import abrir_navegador, acessar
from .planilha import Registro, ler_registros
from .resultado import Resultado, interpretar_mensagem, salvar_json

logger = logging.getLogger(__name__)

TENTATIVAS_POR_REGISTRO = 2


def _processar_registro(
    driver: WebDriver,
    espera: WebDriverWait,
    registro: Registro,
    numero: int,
    ultimo: bool,
) -> None:
    """Mapeia os campos da rodada atual, preenche o registro e submete.

    O formulário é remapeado a cada tentativa: se o Angular recriar os inputs
    no meio do preenchimento, as referências anteriores ficam obsoletas.
    Depois do último registro o formulário não é recriado — a página passa a
    exibir o resultado —, então não faz sentido esperar por uma nova rodada.
    """
    for tentativa in range(1, TENTATIVAS_POR_REGISTRO + 1):
        try:
            campos = mapear_campos(driver, espera)
            preencher(campos, vars(registro))
            ancora = submeter(driver, espera)
            if not ultimo:
                aguardar_novo_formulario(driver, espera, ancora)
            return
        except StaleElementReferenceException:
            if tentativa == TENTATIVAS_POR_REGISTRO:
                raise ErroFormulario(
                    f"registro {numero} não pôde ser preenchido: "
                    f"o formulário foi recriado durante o preenchimento"
                )
            logger.warning(
                "Registro %d: formulário recriado durante o preenchimento, "
                "tentativa %d de %d",
                numero,
                tentativa + 1,
                TENTATIVAS_POR_REGISTRO,
            )


def executar(config: Config) -> tuple[Resultado, dict]:
    """Executa o desafio de ponta a ponta e devolve resultado e evidências."""
    config.preparar_diretorios()
    inicio = datetime.now(timezone.utc)
    logger.info("Iniciando execução (headless=%s)", config.headless)

    with abrir_navegador(config) as driver:
        espera = WebDriverWait(driver, config.timeout)

        acessar(driver, config)
        aguardar_pagina(driver, espera)

        caminho = baixar_planilha(driver, config)
        registros = ler_registros(caminho)

        iniciar_desafio(driver, espera)
        for numero, registro in enumerate(registros, start=1):
            logger.info(
                "Preenchendo registro %d/%d (%s)",
                numero,
                len(registros),
                rodada_atual(driver) or "rodada desconhecida",
            )
            _processar_registro(
                driver, espera, registro, numero, ultimo=numero == len(registros)
            )

        mensagem = capturar_resultado(driver, espera)
        logger.info("Resultado do site: %s", mensagem)

        screenshot = config.dir_artifacts / "resultado.png"
        driver.save_screenshot(str(screenshot))
        logger.info("Screenshot salvo em %s", screenshot.name)

    fim = datetime.now(timezone.utc)
    resultado = interpretar_mensagem(mensagem)
    execucao = {
        "url": config.url,
        "headless": config.headless,
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "duracao_execucao_s": round((fim - inicio).total_seconds(), 2),
        "planilha": caminho.name,
        "registros_lidos": len(registros),
        "registros_submetidos": len(registros),
        "screenshot": screenshot.name,
    }
    salvar_json(config.dir_artifacts / "resultado.json", resultado, execucao)

    logger.info(
        "Concluído: %d registros, acurácia %d%% (%d de %d campos) em %d ms",
        len(registros),
        resultado.acuracia_percentual,
        resultado.campos_preenchidos,
        resultado.campos_totais,
        resultado.duracao_desafio_ms,
    )
    return resultado, execucao
