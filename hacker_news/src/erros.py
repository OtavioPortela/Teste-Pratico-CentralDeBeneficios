"""Erros de domínio da carga incremental.

Cada erro marca uma condição em que não é seguro continuar, para que a falha
apareça com diagnóstico em vez de virar um buraco silencioso no intervalo
processado.
"""


class ErroCarga(Exception):
    """Erro base do processo de carga."""


class ErroAPI(ErroCarga):
    """A API do Hacker News não respondeu de forma utilizável."""


class ErroBanco(ErroCarga):
    """O banco local não pôde ser aberto, criado ou atualizado."""
