"""Ponto de entrada da carga incremental do Hacker News.

Uso:
    python main.py                      # inicial na primeira vez, incremental depois
    python main.py --initial-limit 50   # muda o tamanho só da carga inicial
"""

import argparse
import logging
import sys

from src.carga import executar
from src.config import DIR_ARTIFACTS, LIMITE_INICIAL, Config
from src.erros import ErroCarga
from src.resultado import formatar

logger = logging.getLogger("hacker_news")


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
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def analisar_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Carga incremental da API pública do Hacker News"
    )
    parser.add_argument(
        "--initial-limit",
        type=int,
        default=LIMITE_INICIAL,
        help=f"quantidade de IDs da carga inicial (padrão: {LIMITE_INICIAL})",
    )
    return parser.parse_args()


def main() -> int:
    argumentos = analisar_argumentos()
    if argumentos.initial_limit < 1:
        print("--initial-limit precisa ser maior que zero", file=sys.stderr)
        return 2

    configurar_logs()
    config = Config(limite_inicial=argumentos.initial_limit)

    try:
        resumo = executar(config)
    except ErroCarga as erro:
        logger.error("Carga interrompida: %s", erro)
        return 1

    print()
    print(formatar(resumo))
    return 1 if resumo.interrompida else 0


if __name__ == "__main__":
    sys.exit(main())
