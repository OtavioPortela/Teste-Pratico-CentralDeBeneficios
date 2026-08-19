# RPA Challenge

Parte 1 do teste técnico. O desafio é automatizar o [RPA Challenge](https://rpachallenge.com/):
baixar a planilha disponibilizada pelo site, preencher os formulários das 10 rodadas e
concluir sem intervenção manual. A dificuldade está no formulário, que embaralha os campos
a cada envio — a automação não pode depender da posição em que eles aparecem.

## Solução entregue

- Acessa o site e baixa a planilha pelo próprio fluxo do navegador, sem arquivo colocado à mão.
- Lê os registros com OpenPyXL, normalizando cabeçalhos e preservando os valores originais.
- Identifica cada campo pelo rótulo exibido na tela, e não pela ordem ou posição.
- Remapeia o formulário depois de cada envio, já que o site recria os elementos.
- Executa em modo headless (padrão) ou com janela visível, com o mesmo comportamento.
- Registra evidências da execução em `artifacts/`.

## Tecnologias

Python · Selenium · OpenPyXL · Pytest

Requer Google Chrome instalado; o driver é resolvido automaticamente pelo Selenium.

## Resultado

| | |
|---|---|
| **Acurácia** | **100%** |
| **Campos preenchidos** | **70 de 70** |
| **Registros processados** | **10** |
| **Testes automatizados** | **26 passed** |

Validado nos dois modos de execução. A tela final do desafio está registrada em
[`artifacts/resultado.png`](artifacts/resultado.png).

## Como executar

```bash
pip install -r requirements.txt
python main.py                # headless
python main.py --no-headless  # acompanhando pelo navegador
```

A execução termina com código `0` apenas quando o site confirma 100% de acurácia.

## Testes

```bash
python -m pytest
```

```text
26 passed
```

Cobrem o que quebra silenciosamente: leitura e validação da planilha, normalização dos
dados (cabeçalhos com espaço extra, telefone que não pode virar notação científica),
o mapeamento entre os campos da planilha e os rótulos da tela, e a interpretação da
mensagem de resultado. São determinísticos e não abrem o navegador.

## Evidências

```text
artifacts/
├── resultado.png    tela final do desafio
├── resultado.json   acurácia, campos, tempos e contagens da execução
└── execucao.log     log completo
```

Os arquivos são regravados a cada execução e comprovam o resultado sem depender de rodar
o projeto novamente.

## Limitações

- Depende do site estar no ar; o carregamento inicial ocasionalmente demora além do limite,
  tratado com uma segunda tentativa de acesso.
- O site tem seletor de idioma: se os rótulos forem traduzidos, o vocabulário usado no
  mapeamento precisa ser complementado.

## Uso de IA

Ferramentas de IA foram usadas como apoio durante o desenvolvimento: reconhecimento do
comportamento do site, discussão de abordagens, escrita de código e testes, revisão e
documentação. As decisões técnicas foram tomadas e revisadas por mim, e o resultado
registrado em `artifacts/` vem de execução real, validada nos dois modos.
