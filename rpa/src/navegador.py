"""Criação do Chrome usado na automação.

O diretório de download aponta para a pasta de dados do projeto, para que a
planilha baixada nunca dependa da pasta de downloads do avaliador.
"""

import logging
from contextlib import contextmanager
from typing import Iterator

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver

from .config import Config
from .erros import ErroNavegacao

logger = logging.getLogger(__name__)

TENTATIVAS_ACESSO = 2


def _opcoes(config: Config) -> Options:
    opcoes = Options()
    if config.headless:
        opcoes.add_argument("--headless=new")
    opcoes.add_argument("--window-size=1440,900")
    # A SPA fica utilizável no DOMContentLoaded; esperar por todos os recursos
    # externos da página só adiciona instabilidade.
    opcoes.page_load_strategy = "eager"
    opcoes.add_argument("--disable-gpu")
    opcoes.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(config.dir_dados),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )
    return opcoes


@contextmanager
def abrir_navegador(config: Config) -> Iterator[WebDriver]:
    """Abre o Chrome e garante o encerramento ao final da execução."""
    logger.info("Abrindo Chrome (headless=%s)", config.headless)
    driver = webdriver.Chrome(options=_opcoes(config))
    driver.set_page_load_timeout(config.timeout)
    try:
        yield driver
    finally:
        driver.quit()
        logger.info("Chrome encerrado")


def acessar(driver: WebDriver, config: Config) -> None:
    """Abre a página do desafio, falhando com mensagem útil se indisponível.

    O carregamento inicial ocasionalmente estoura o tempo limite por lentidão
    do site, por isso uma segunda tentativa antes de desistir.
    """
    logger.info("Acessando %s", config.url)
    for tentativa in range(1, TENTATIVAS_ACESSO + 1):
        try:
            driver.get(config.url)
            return
        except (TimeoutException, WebDriverException) as erro:
            if tentativa == TENTATIVAS_ACESSO:
                raise ErroNavegacao(
                    f"não foi possível abrir {config.url}: {type(erro).__name__}"
                ) from erro
            logger.warning(
                "Falha ao acessar a página (%s); tentativa %d de %d",
                type(erro).__name__,
                tentativa + 1,
                TENTATIVAS_ACESSO,
            )
