# Teste Prático — Central dos Benefícios

Implementação dos dois desafios do teste técnico para Desenvolvedor Sênior de Automação
e Integração:

1. **Automação RPA** — preenchimento do formulário dinâmico do [RPA Challenge](https://rpachallenge.com/).
2. **Carga incremental** — consumo da API pública do Hacker News com persistência local.

Cada desafio vive em seu próprio diretório, com dependências, testes e documentação próprios.

## Visão geral

| Desafio | Objetivo | Tecnologias |
|---|---|---|
| [RPA Challenge](rpa/README.md) | Baixar a planilha e preencher as 10 rodadas do formulário dinâmico | Python, Selenium, OpenPyXL |
| [Hacker News](hacker_news/README.md) | Carga incremental idempotente com estado e persistência local | Python, Requests, SQLite |

## Parte 1 — RPA Challenge

A automação acessa o site, baixa a planilha pelo próprio fluxo do navegador, lê os
registros com OpenPyXL e preenche todas as rodadas do formulário sem intervenção manual.

Como o desafio embaralha os campos a cada envio, cada input é localizado pelo significado
do seu rótulo, e não pela posição na tela — o mapeamento é refeito a cada rodada. A
execução funciona em modo headless e com janela visível, e cada rodada produz evidências
em `rpa/artifacts/`.

**Resultado validado: 100% de acurácia — 70 de 70 campos.** Suíte com **26 testes**
passando.

Detalhes de implementação, decisões e limitações: [`rpa/README.md`](rpa/README.md).

## Parte 2 — Hacker News

O processo consulta a API oficial do Hacker News, faz uma carga inicial limitada aos
últimos 100 IDs e, nas execuções seguintes, processa apenas o intervalo novo — controlado
por um watermark guardado explicitamente no banco.

Os itens são persistidos em SQLite com campos consultáveis e o JSON bruto preservado. O ID
é chave única, então reexecutar nunca duplica registros. As requisições têm timeout, retries
limitados e backoff; se um ID falhar em definitivo, a execução para ali e o watermark não
avança, para não deixar buracos no intervalo processado. Cada execução gera um relatório
com faixa, contagens e duração.

Validação contra a API real: carga inicial de 100 IDs, segunda execução consultando
apenas os 3 IDs novos, e `COUNT(*) == COUNT(DISTINCT id)` no banco após reprocessamento
deliberado. Suíte com **48 testes** passando, nenhum deles dependendo da rede.

Detalhes de implementação, decisões e limitações: [`hacker_news/README.md`](hacker_news/README.md).

## Estrutura

```text
.
├── rpa/                  Parte 1 — automação do RPA Challenge
│   ├── src/
│   ├── tests/
│   ├── artifacts/
│   └── README.md
│
├── hacker_news/          Parte 2 — carga incremental do Hacker News
│   ├── src/
│   ├── tests/
│   ├── artifacts/
│   └── README.md
│
├── .gitignore
└── README.md
```

## Como executar

Cada projeto tem seu próprio `requirements.txt`; as instruções completas, incluindo o
ambiente virtual, estão nos READMEs de cada desafio. A Parte 1 precisa do Google Chrome
instalado; a Parte 2 cria o banco SQLite sozinha na primeira execução.

```bash
cd rpa
pip install -r requirements.txt
python main.py          # --no-headless para acompanhar pelo navegador
python -m pytest
```

```bash
cd hacker_news
pip install -r requirements.txt
python main.py          # carga inicial na primeira vez, incremental nas seguintes
python -m pytest
```

## Resultados

| Item | Resultado |
|---|---|
| RPA Challenge | 100% de acurácia — 70/70 campos, 10 registros |
| Testes da Parte 1 | 26 passed |
| Hacker News — carga inicial | 100 IDs consultados, 100 itens persistidos |
| Hacker News — carga incremental | 3 IDs consultados na segunda execução |
| Duplicidade no banco | nenhuma — 103 registros, 103 IDs distintos |
| Testes da Parte 2 | 48 passed |
| Total | 74 testes |

## Decisões principais

- **Selenium e OpenPyXL na Parte 1** — padrão de mercado para navegador em Python, com
  esperas explícitas suficientes para o desafio; OpenPyXL dá conta de uma planilha de 10
  linhas sem trazer Pandas junto.
- **Campos por significado, não por posição** — o rótulo é a única âncora estável do
  formulário; ids e ordem dos elementos mudam a cada envio.
- **Requests e SQLite na Parte 2** — chamadas sequenciais simples ao mesmo host e duas
  tabelas de dados não justificam cliente assíncrono nem ORM.
- **Watermark explícito** — o estado da carga fica em tabela própria, separado dos dados,
  em vez de ser inferido do maior ID persistido.
- **Avanço conservador** — falha definitiva em um ID interrompe a execução; é preferível
  parar a criar um intervalo com lacunas silenciosas.
- **Ferramentas proporcionais ao problema** — nenhuma dependência entrou sem uso real no
  código.

## Evidências

Cada projeto guarda em `artifacts/` o que foi produzido nas execuções reais:

- **`rpa/artifacts/`** — screenshot da tela final do desafio, resultado estruturado em
  JSON e log da execução.
- **`hacker_news/artifacts/`** — resumo estruturado da carga em JSON e log da execução.

## Uso de IA

Ferramentas de IA foram usadas como apoio ao longo do desenvolvimento: exploração do
comportamento das aplicações, discussão de abordagens, escrita de código e testes,
revisão e apoio na documentação.

As decisões de arquitetura foram tomadas e revisadas por mim, e todo comportamento
descrito aqui foi verificado por execução real e pelas suítes de testes que acompanham a
entrega.

---

Detalhes técnicos, decisões específicas e limitações conhecidas de cada desafio estão nos
READMEs de [`rpa/`](rpa/README.md) e [`hacker_news/`](hacker_news/README.md).
