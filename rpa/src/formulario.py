"""Interação com o formulário dinâmico do RPA Challenge.

O desafio embaralha a ordem dos campos e regenera os atributos `id`/`name` a
cada submit; o que permanece estável é o texto do `<label>` ao lado de cada
input. Por isso os campos são localizados pelo rótulo, nunca por posição,
índice ou id, e os elementos são remapeados a cada rodada.
"""

import logging
from typing import Mapping

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .erros import ErroFormulario, ErroResultado

logger = logging.getLogger(__name__)

# Os labels não têm atributo "for": o input é o irmão seguinte do label.
CAMPOS = (By.XPATH, "//form//label/following-sibling::input[1]")
BOTAO_INICIAR = (By.CSS_SELECTOR, "button.uiColorButton")
BOTAO_SUBMETER = (By.CSS_SELECTOR, "form input[type='submit']")
RESULTADO = (By.CSS_SELECTOR, "div.congratulations div.message2")

# Rótulo exibido na tela -> campo do registro.
ROTULOS = {
    "first name": "first_name",
    "last name": "last_name",
    "company name": "company_name",
    "role in company": "role_in_company",
    "address": "address",
    "email": "email",
    "phone number": "phone_number",
}


def normalizar_rotulo(texto: str) -> str:
    """Normaliza o texto do label para comparação estável."""
    return " ".join(str(texto).split()).lower()


def aguardar_pagina(driver: WebDriver, espera: WebDriverWait) -> None:
    """Confirma que a página do desafio está pronta para uso."""
    try:
        espera.until(EC.element_to_be_clickable(BOTAO_INICIAR))
    except TimeoutException as erro:
        raise ErroFormulario(
            f"página do desafio não carregou: {driver.current_url}"
        ) from erro


def iniciar_desafio(driver: WebDriver, espera: WebDriverWait) -> None:
    """Clica em START, o que inicia o cronômetro do desafio."""
    espera.until(EC.element_to_be_clickable(BOTAO_INICIAR)).click()
    espera.until(lambda _: len(driver.find_elements(*CAMPOS)) == len(ROTULOS))
    logger.info("Desafio iniciado")


def mapear_campos(driver: WebDriver, espera: WebDriverWait) -> dict[str, WebElement]:
    """Mapeia cada campo do registro ao input correspondente na tela atual."""
    try:
        espera.until(lambda _: len(driver.find_elements(*CAMPOS)) == len(ROTULOS))
    except TimeoutException as erro:
        raise ErroFormulario(
            f"esperados {len(ROTULOS)} campos no formulário, "
            f"encontrados {len(driver.find_elements(*CAMPOS))}"
        ) from erro

    mapa: dict[str, WebElement] = {}
    rotulos_vistos: list[str] = []
    for entrada in driver.find_elements(*CAMPOS):
        rotulo = entrada.find_element(By.XPATH, "./preceding-sibling::label[1]").text
        rotulos_vistos.append(rotulo)
        campo = ROTULOS.get(normalizar_rotulo(rotulo))
        if campo:
            mapa[campo] = entrada

    faltando = sorted(set(ROTULOS.values()) - set(mapa))
    if faltando:
        raise ErroFormulario(
            f"campos não localizados pelo rótulo: {faltando}. "
            f"Rótulos na tela: {rotulos_vistos}"
        )
    return mapa


def preencher(campos: Mapping[str, WebElement], valores: Mapping[str, str]) -> None:
    """Digita cada valor no input correspondente ao seu significado."""
    for campo, entrada in campos.items():
        entrada.clear()
        entrada.send_keys(valores[campo])


def submeter(driver: WebDriver, espera: WebDriverWait) -> WebElement:
    """Envia o formulário e devolve um input da rodada atual como âncora.

    A âncora serve para detectar, por staleness, que o Angular recriou o
    formulário — os elementos da rodada anterior deixam de existir no DOM.
    """
    ancora = driver.find_elements(*CAMPOS)[0]
    espera.until(EC.element_to_be_clickable(BOTAO_SUBMETER)).click()
    return ancora


def aguardar_novo_formulario(
    driver: WebDriver, espera: WebDriverWait, ancora: WebElement
) -> None:
    """Aguarda o formulário ser recriado depois de um submit."""
    try:
        espera.until(EC.staleness_of(ancora))
        espera.until(lambda _: len(driver.find_elements(*CAMPOS)) == len(ROTULOS))
    except TimeoutException as erro:
        raise ErroFormulario("formulário não foi atualizado após o submit") from erro


def rodada_atual(driver: WebDriver) -> str:
    """Texto do botão de estado do desafio: START, ROUND n ou RESET."""
    botoes = driver.find_elements(*BOTAO_INICIAR)
    return botoes[0].text.strip() if botoes else ""


def capturar_resultado(driver: WebDriver, espera: WebDriverWait) -> str:
    """Aguarda e devolve a mensagem final do desafio.

    No fim da última rodada o formulário deixa de existir e a página exibe
    "Your success rate is ... in ... milliseconds".
    """
    try:
        elemento = espera.until(EC.visibility_of_element_located(RESULTADO))
        texto = elemento.text.strip()
    except (TimeoutException, StaleElementReferenceException) as erro:
        raise ErroResultado("mensagem de resultado não encontrada na página") from erro

    if not texto:
        raise ErroResultado("mensagem de resultado veio vazia")
    return texto
