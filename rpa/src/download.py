"""Download da planilha pelo próprio fluxo do navegador."""

import logging
from pathlib import Path

from selenium.common.exceptions import NoSuchWindowException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .config import Config
from .erros import ErroDownload

logger = logging.getLogger(__name__)

# O botão "DOWNLOAD EXCEL" é um link direto para o arquivo do desafio.
SELETOR_DOWNLOAD = (By.CSS_SELECTOR, "a[href$='.xlsx']")


def _download_concluido(destino: Path) -> bool:
    """O Chrome só renomeia o .crdownload quando termina de gravar o arquivo."""
    parciais = list(destino.parent.glob("*.crdownload"))
    return destino.is_file() and not parciais


def _voltar_para_o_desafio(driver: WebDriver, janela_original: str) -> None:
    """Fecha a aba aberta pelo link e devolve o foco à janela do desafio.

    O link usa target="_blank": fechar essa aba antes do fim da transferência
    cancela o download, por isso a limpeza acontece só depois da espera.
    """
    for janela in [j for j in driver.window_handles if j != janela_original]:
        try:
            driver.switch_to.window(janela)
            driver.close()
        except NoSuchWindowException:
            pass  # a aba já se fechou sozinha
    driver.switch_to.window(janela_original)


def baixar_planilha(driver: WebDriver, config: Config) -> Path:
    """Clica no botão de download e devolve o caminho da planilha baixada."""
    destino = config.planilha
    destino.unlink(missing_ok=True)  # garante que o arquivo lido é o desta execução
    for parcial in destino.parent.glob("*.crdownload"):
        parcial.unlink()

    janela_original = driver.current_window_handle
    espera = WebDriverWait(driver, config.timeout)
    logger.info("Iniciando download da planilha")
    espera.until(EC.element_to_be_clickable(SELETOR_DOWNLOAD)).click()

    try:
        WebDriverWait(driver, config.timeout_download, poll_frequency=0.2).until(
            lambda _: _download_concluido(destino)
        )
    except TimeoutException as erro:
        raise ErroDownload(
            f"download não concluído em {config.timeout_download}s; "
            f"esperado {destino}"
        ) from erro
    finally:
        _voltar_para_o_desafio(driver, janela_original)

    logger.info(
        "Download concluído: %s (%d bytes)", destino.name, destino.stat().st_size
    )
    return destino
