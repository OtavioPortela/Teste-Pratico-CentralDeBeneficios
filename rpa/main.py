"""Ponto de entrada do RPA Challenge.

Uso:
    python main.py                # headless (padrão)
    python main.py --no-headless  # com janela visível
"""

import argparse
import logging
import sys

from src.config import DIR_ARTIFACTS, Config
from src.desafio import executar
from src.erros import ErroDesafio

ACURACIA_EXIGIDA = 100

logger = logging.getLogger("rpa")


def configurar_logs() -> None:
    DIR_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(DIR_ARTIFACTS / "execucao.log", encoding="utf-8"),
        ],
    )
    logging.getLogger("selenium").setLevel(logging.WARNING)


def analisar_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automação do RPA Challenge")
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="executa o Chrome sem janela (padrão: headless)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="tempo máximo de espera por elemento, em segundos",
    )
    return parser.parse_args()


def main() -> int:
    argumentos = analisar_argumentos()
    configurar_logs()
    config = Config(headless=argumentos.headless, timeout=argumentos.timeout)

    try:
        resultado, _ = executar(config)
    except ErroDesafio as erro:
        logger.error("Execução interrompida: %s", erro)
        return 1

    if resultado.acuracia_percentual != ACURACIA_EXIGIDA:
        logger.error(
            "Acurácia de %d%% abaixo do exigido (%d%%)",
            resultado.acuracia_percentual,
            ACURACIA_EXIGIDA,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
