"""Erros de domínio do desafio.

Cada erro representa uma condição em que não é seguro continuar a execução,
para que a falha seja explícita em vez de silenciosa.
"""


class ErroDesafio(Exception):
    """Erro base do RPA Challenge."""


class ErroNavegacao(ErroDesafio):
    """A página do desafio não pôde ser aberta."""


class ErroDownload(ErroDesafio):
    """A planilha não ficou disponível no diretório de download."""


class ErroPlanilha(ErroDesafio):
    """A planilha não existe, está vazia ou não tem a estrutura esperada."""


class ErroFormulario(ErroDesafio):
    """O formulário não pôde ser mapeado, preenchido ou atualizado."""


class ErroResultado(ErroDesafio):
    """O resultado final do desafio não foi encontrado na página."""
