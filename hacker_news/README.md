# Hacker News — Carga Incremental

Parte 2 do teste técnico. O desafio é consumir a API pública do Hacker News, persistir os
itens em uma base local e permitir que o processo seja executado várias vezes sem criar
duplicidade — processando apenas o que ainda não foi processado.

## Solução entregue

- **Carga inicial** limitada aos últimos 100 IDs a partir do `maxitem` da API.
- **Execuções seguintes** consultam somente os IDs novos, a partir do último processado.
- **Watermark** guardado explicitamente no banco, em tabela própria, separado dos dados.
- **Persistência em SQLite**, com campos consultáveis em colunas e o JSON bruto preservado.
- **Idempotência** garantida pelo banco: o ID do Hacker News é a chave única.
- **Retries com backoff** e timeout em todas as requisições.
- **Comportamento conservador**: se um ID falha em definitivo, a execução para ali e o
  watermark não avança, para não deixar lacunas no intervalo processado.
- **Relatório** ao final de cada execução, com faixa, contagens e duração.

Uma resposta `null` da API (ID inexistente ou removido) não é falha: o item é contado como
ignorado e o processo segue em frente.

## Tecnologias

Python · Requests · SQLite (`sqlite3` da biblioteca padrão) · Pytest

## Resultados

Números das execuções reais contra a API.

| Execução | Faixa | Consultados | Inseridos | Falhas |
|---|---|---|---|---|
| 1ª — carga inicial | `49359597 → 49359696` | 100 | 100 | 0 |
| 2ª — incremental | `49359697 → 49359699` | **3** | 3 | 0 |

Na segunda execução os 100 IDs anteriores não foram consultados de novo, e o tempo caiu de
17,3 s para 0,8 s.

**Idempotência:** em um reprocessamento controlado de IDs já persistidos, nenhum registro
duplicado foi criado — `COUNT(*) == COUNT(DISTINCT id)`, hoje 103 registros e 103 IDs
distintos.

**Testes:** 48 testes automatizados passando, nenhum deles dependendo da rede.

## Como executar

```bash
pip install -r requirements.txt
python main.py
```

Na primeira execução é feita a carga inicial e o banco é criado automaticamente. Nas
seguintes, o processo continua a partir do último ID processado; se não houver IDs novos,
a execução informa isso e termina com sucesso. O argumento `--initial-limit N` altera o
tamanho da carga inicial (padrão: 100).

## Testes

```bash
python -m pytest
```

```text
48 passed
```

Cobrem os riscos reais do processo: o cliente da API (timeout, retries, `null`, erros
definitivos), o cálculo das faixas inicial e incremental, a persistência em SQLite, o
avanço do watermark, o comportamento em falha, a idempotência e a contabilização das
métricas do relatório.

## Evidências

```text
artifacts/
├── resumo.json      métricas da última execução
└── execucao.log     log completo das execuções
```

## Limitações

- O endpoint opcional `updates.json` não foi implementado: itens que mudam depois de
  persistidos só seriam atualizados se voltassem a ser processados.
- Um ID que falhe de forma persistente bloqueia o avanço da carga até ser resolvido — é a
  contrapartida assumida do comportamento conservador.

## Uso de IA

Ferramentas de IA foram usadas como apoio durante o desenvolvimento: exploração da API,
discussão de abordagens, escrita de código e testes, revisão e documentação. As decisões
de arquitetura foram tomadas e revisadas por mim, e os resultados apresentados vêm de
execução real contra a API pública.
