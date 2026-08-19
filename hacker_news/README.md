# Parte 2 — Carga incremental com a API do Hacker News

Processo de carga incremental em Python que consome a API pública do Hacker News,
persiste os itens em SQLite e pode ser reexecutado quantas vezes for necessário sem
criar duplicidade. Cada execução processa apenas o intervalo novo e produz um
relatório com as métricas da operação.

## Requisitos

- Python 3.10+
- Acesso à internet (a API é pública, sem chave nem autenticação)

## Instalação

```bash
cd hacker_news
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Execução

```bash
python main.py                     # inicial na primeira vez, incremental nas seguintes
python main.py --initial-limit 50  # muda apenas o tamanho da carga inicial
```

Não há preparação manual de banco: na primeira execução o arquivo, as tabelas e os
índices são criados automaticamente em `data/hacker_news.db`.

Códigos de saída: `0` em execução bem-sucedida (inclusive quando não há item novo),
`1` quando a carga é interrompida por falha, `2` para argumento inválido.

## Carga inicial

Quando não existe estado anterior, o processo consulta `GET /maxitem.json` e trabalha
sobre os **últimos 100 IDs**:

```text
maxitem = 49359696   →   faixa 49359597 → 49359696   (100 IDs)
```

São 100 **IDs consultados**, não 100 itens válidos: se alguns responderem `null`, eles
entram como ignorados e o total inserido é menor. Isso aparece nas métricas.

## Carga incremental

Nas execuções seguintes, o intervalo sai do estado gravado:

```text
last_item_id + 1  →  maxitem
```

Exemplo real da segunda execução deste projeto: watermark `49359696`, maxitem
`49359699`, faixa `49359697 → 49359699` — apenas 3 IDs consultados. Os 100 IDs da carga
inicial não são consultados de novo.

Se `last_item_id == maxitem`, não há o que fazer: a execução informa
`Nenhum item novo para processar.`, contabiliza tudo zerado e termina com sucesso.

## Watermark conservador

O estado fica em uma tabela própria (`sync_state`, chave `last_item_id`), separado dos
dados. Ele **não** é inferido de `MAX(id)` dos itens: estado do pipeline e dados
persistidos são coisas diferentes — um item pode existir no banco sem que o intervalo
até ele tenha sido percorrido.

Os IDs são processados sequencialmente, em ordem crescente. **Em caso de falha
definitiva em um ID, a execução é interrompida e o watermark permanece no último ID
processado com sucesso.** Os IDs seguintes não são consultados, e a próxima execução
recomeça exatamente do ID que falhou.

```text
101 ✅  102 ✅  103 ❌ (após os retries)
→ execução para em 103
→ last_item_id = 102
→ próxima execução começa em 103
```

O princípio: é melhor interromper o avanço do que criar um buraco silencioso no
intervalo processado. A persistência do item e a atualização do watermark acontecem na
**mesma transação SQLite**, então nunca existe um estado em que o watermark passou de um
ID que não foi gravado.

## Tratamento de `null`

A API responde `null` para IDs que não existem ou foram removidos. Isso é uma resposta
HTTP bem-sucedida, não uma falha técnica:

```text
null  →  consultado + processado + ignorado  →  watermark avança  →  segue para o próximo
```

Já um timeout ou erro de conexão que sobrevive a todas as tentativas é falha: o
watermark não avança e a execução para. Essa distinção é o ponto mais importante do
pipeline e está coberta por testes dedicados.

## Idempotência

`items.id` é a chave primária — a identidade natural do Hacker News. Quem impede
duplicidade é o **banco**, não uma checagem no código: mesmo um `INSERT` cru com ID
repetido é recusado com `IntegrityError`.

Ao reprocessar um ID já persistido, o `INSERT ... ON CONFLICT(id) DO UPDATE` faz um
upsert e a execução contabiliza o registro como **atualizado**. Escolhi upsert em vez de
simplesmente pular porque itens do Hacker News mudam depois de criados (score, contagem
de comentários, flags `dead`/`deleted`), então regravar deixa a base mais correta sem
custo adicional — e mantém a métrica `atualizados`, pedida no relatório, com significado
real. A consulta que decide entre "inserido" e "atualizado" serve apenas para a métrica.

Validação feita com a API real: em uma cópia do banco, o watermark foi recuado em 10
IDs e a carga reexecutada — resultado: 10 atualizados, nenhuma linha nova para esses IDs,
`COUNT(*) == COUNT(DISTINCT id)`.

## Persistência

SQLite (`sqlite3` da biblioteca padrão), arquivo em `data/hacker_news.db`.

```sql
items(
  id INTEGER PRIMARY KEY,   -- chave única por item
  type, author, time, title, url, score, parent, descendants, deleted, dead,
  raw_json TEXT NOT NULL,   -- payload completo, como veio da API
  fetched_at TEXT NOT NULL  -- quando este projeto gravou o registro
)
sync_state(chave TEXT PRIMARY KEY, valor INTEGER NOT NULL, atualizado_em TEXT NOT NULL)
```

Índices em `type` e `time`. A coluna `author` guarda o campo `by` da API (`by` é palavra
reservada em SQL e exigiria aspas em toda consulta).

Os campos consultáveis foram escolhidos olhando payloads reais dos cinco tipos que a API
retorna (`story`, `comment`, `job`, `poll`, `pollopt`), que têm chaves diferentes entre
si. O que não virou coluna — `text`, `kids`, `parts`, `poll` — continua preservado
integralmente em `raw_json`:

```text
API JSON
   ├── campos relevantes → colunas SQLite
   └── objeto completo   → raw_json
```

## Retries e backoff

Cada requisição tem `timeout` explícito (10s por padrão) e no máximo **3 tentativas**,
com backoff exponencial de 0,5s e 1,0s. São repetidos apenas os erros que podem melhorar
sozinhos: timeout, erro de conexão, status transitório (429, 500, 502, 503, 504) e corpo
ilegível. Um `4xx` definitivo falha na hora, sem insistir. Cada tentativa frustrada é
registrada em `WARNING` com o ID, o número da tentativa e o tipo da falha.

Os parâmetros ficam em `src/config.py` (`timeout`, `tentativas`, `backoff_inicial`).

## Relatório

Cada execução imprime no terminal e grava em `artifacts/resumo.json`:

```text
Carga incremental concluída

Tipo: incremental
Faixa: 49359697 → 49359699
Consultados: 3
Inseridos: 3
Atualizados: 0
Ignorados: 0
Falhas: 0
Watermark inicial: 49359696
Watermark final: 49359699
Duração: 0.81 s
```

Quando a carga é interrompida, o relatório mostra a faixa planejada, o último ID
processado, o ID que falhou e o motivo. As evidências ficam em `artifacts/`
(`resumo.json` e `execucao.log`).

## Testes

```bash
python -m pytest
```

**48 testes, nenhum deles toca a rede** — a `requests.Session` é substituída por um dublê
e o banco usa arquivos temporários. Riscos protegidos:

| Arquivo | O que protege |
|---|---|
| `test_faixa.py` | cálculo do intervalo: últimos 100 IDs, maxitem menor que o limite, incremental a partir do watermark, faixa vazia, maxitem retrocedido |
| `test_api.py` | timeout em toda chamada, retry com backoff crescente, `null` como resposta válida, 4xx sem retry, falha após esgotar tentativas |
| `test_banco.py` | criação do schema, chave primária, `IntegrityError` em ID duplicado, campos nas colunas certas, `raw_json` idêntico ao payload, leitura/gravação/atualização do estado |
| `test_carga.py` | `null` que avança o watermark, falha definitiva que interrompe e **não** consulta os IDs seguintes, retomada a partir do ID que falhou, reprocessamento sem duplicidade, segunda execução consultando só o intervalo novo |
| `test_resultado.py` | contabilização das métricas exigidas pelo PDF nos três cenários de relatório |

## Decisões técnicas

**`requests`** — a carga faz dezenas de chamadas sequenciais ao mesmo host; `requests`
resolve isso com API mínima, e a `Session` reaproveita a conexão TCP/TLS. Não há ganho em
`httpx` ou async aqui: o gargalo é a própria API, e o processamento precisa ser
sequencial por decisão de projeto.

**`sqlite3` da biblioteca padrão, sem ORM** — são duas tabelas e meia dúzia de consultas.
Um ORM adicionaria dependência, camada de mapeamento e uma linguagem a mais para explicar,
sem resolver nada que o SQL direto já resolva. O `ON CONFLICT` do SQLite, que é o coração
da idempotência, fica explícito no código.

**Sem framework web** — isto é um processo de linha de comando executado sob demanda, não
um serviço. Não há endpoint a servir nem processo a manter no ar.

**Carga inicial limitada a 100 IDs** — o PDF pede carga inicial limitada e não exige o
histórico. 100 IDs demonstram o mecanismo e mantêm a execução em ~17s.

**Processamento sequencial** — paralelizar quebraria a garantia central: com requisições
concorrentes, o watermark deixaria de significar "todos os IDs até aqui foram
processados". A ordem crescente é o que permite parar em um ponto seguro.

**Watermark conservador** — descrito acima. É a decisão que troca throughput por
integridade do intervalo.

## Limitações

- `updates.json` não foi implementado: itens antigos que mudam depois de já persistidos
  só seriam corrigidos se voltassem a ser processados. O endpoint é opcional no PDF, e a
  base de upsert já está pronta para receber essa fonte.
- Um ID que falha de forma persistente (por exemplo, um item que faz a API responder 500
  indefinidamente) bloqueia todo o avanço da carga até ser resolvido. É a consequência
  aceita do modelo conservador; um `--skip-id` ou uma fila de pendências resolveria, ao
  custo de complexidade que este escopo não pede.
- Não há paginação ou limite máximo por execução na carga incremental: se o processo
  ficar muitos dias sem rodar, a faixa pode ficar grande e a execução, longa.
- O relatório em `artifacts/resumo.json` guarda apenas a última execução; o histórico
  completo fica no `execucao.log`.
- Os testes cobrem a lógica do pipeline, não a API real: uma mudança de contrato do
  Hacker News só apareceria em execução.

## Uso de IA

Este projeto foi desenvolvido com apoio do Claude Code (Anthropic), usado para
exploração da API, geração de código, escrita dos testes e revisão. As decisões de
arquitetura — carga inicial limitada, watermark em tabela própria, política conservadora
de falha, distinção entre `null` e erro técnico, escolha das dependências — foram
definidas e revisadas por mim, e todo o comportamento descrito neste README foi validado
por execução real e pela suíte de testes.
