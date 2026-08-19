# Parte 1 — Automação RPA (RPA Challenge)

Automação em Python que baixa a planilha do [RPA Challenge](https://rpachallenge.com/),
lê os registros e preenche as 10 rodadas do formulário dinâmico com 100% de acurácia,
sem intervenção manual.

## Requisitos

- Python 3.10+
- Google Chrome instalado (o driver é resolvido automaticamente pelo Selenium Manager)

## Instalação

```bash
cd rpa
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Execução

```bash
python main.py                # headless (padrão)
python main.py --no-headless  # com janela visível
python main.py --timeout 30   # ajusta a espera máxima por elemento
```

O processo termina com código `0` somente quando o site confirma 100% de acurácia;
qualquer falha ou acurácia menor encerra com código `1`.

## Fluxo

1. Abre o Chrome com o diretório de download apontado para `data/`.
2. Acessa o desafio e clica em **DOWNLOAD EXCEL** — a planilha nunca é colocada à mão.
3. Aguarda a conclusão do download (ausência de `.crdownload`) e lê o arquivo com OpenPyXL.
4. Clica em **START** (é aqui que o cronômetro do site começa).
5. Para cada registro: mapeia os campos pelo rótulo, preenche, submete e espera o
   formulário ser recriado.
6. Captura a mensagem final, o screenshot e grava as evidências em `artifacts/`.

## Estrutura

```
rpa/
├── main.py              # entrada: argumentos, logging e código de saída
├── src/
│   ├── config.py        # caminhos do projeto e parâmetros da execução
│   ├── navegador.py     # Chrome (headless, diretório de download) e acesso à página
│   ├── download.py      # clique no botão e espera pela conclusão do download
│   ├── planilha.py      # OpenPyXL: validação, normalização e registros
│   ├── formulario.py    # mapeamento semântico dos campos e preenchimento
│   ├── desafio.py       # orquestração do fluxo
│   ├── resultado.py     # leitura da mensagem final e gravação do JSON
│   └── erros.py         # erros de domínio
├── tests/               # testes determinísticos (sem navegador)
├── data/                # planilha baixada (entrada, recriada a cada execução)
└── artifacts/           # evidências: JSON, screenshot e log
```

`data/` guarda entrada, `artifacts/` guarda evidência — as duas coisas não se misturam.

## Decisões técnicas

**Selenium.** Escolhido por ser o padrão de mercado para automação de navegador em
Python, com WebDriverWait/`expected_conditions` suficientes para todas as esperas deste
desafio e sem dependência de runtime extra além do Chrome. O Playwright foi usado
apenas para o reconhecimento inicial da página; a solução entregue é só Selenium.

**Campos identificados pelo rótulo.** A investigação do DOM mostrou que, a cada submit,
o Angular recria os inputs com `id`/`name` aleatórios (`nYD7x` → `Fdx8P` → `aDrMu`) e
embaralha a ordem dos elementos no DOM — não é apenas a posição visual que muda. O que
permanece estável é o texto do `<label>`. Como os labels não têm atributo `for`, a
relação é estrutural, e o campo é localizado por
`//form//label/following-sibling::input[1]`, lendo o rótulo de cada input. Nenhum índice,
coordenada, XPath absoluto ou id fixo é usado. O atributo `ng-reflect-name`
(`labelFirstName`, `labelAddress`, …) também é estável, mas só existe porque o site está
publicado em modo de desenvolvimento do Angular — serve como alternativa, não como base.

**Sincronização sem `sleep`.** Cada espera tem um sinal próprio:

| Momento | Sinal |
|---|---|
| Página pronta | botão de estado clicável |
| Download concluído | arquivo presente e sem `.crdownload` |
| Formulário disponível | os 7 pares `label`+`input` presentes |
| Nova rodada | `staleness_of` do input anterior + 7 campos novamente presentes |
| Resultado final | `div.congratulations div.message2` visível |

**Normalização da planilha.** O cabeçalho oficial traz `"Last Name "` com espaço à
direita e o telefone vem como inteiro (`40716543298`). Os cabeçalhos são normalizados
(espaços colapsados, minúsculas) antes do mapeamento, e os valores viram texto
preservando o dado original — sem notação científica e sem `.0` no fim.

**Sem Pandas e sem banco.** A planilha tem 10 linhas: OpenPyXL basta. O estado da
execução vive nos logs e nas evidências; persistência é assunto da Parte 2.

## Evidências

Geradas em `artifacts/` a cada execução:

- `resultado.json` — acurácia, campos preenchidos, duração do desafio, duração total,
  horários, registros lidos/submetidos e modo de execução;
- `resultado.png` — screenshot da mensagem final;
- `execucao.log` — log completo da execução.

Última execução registrada: **100% (70 de 70 campos)**.

## Testes

```bash
python -m pytest
```

Cobrem o que quebra em silêncio: normalização de cabeçalhos e valores, ordem das colunas,
colunas obrigatórias ausentes, linhas em branco e incompletas, o vocabulário que liga
rótulo da tela a campo da planilha e a leitura da mensagem de resultado. São
determinísticos e não abrem navegador.

## Uso de IA

Ferramentas de IA foram usadas como apoio durante o desenvolvimento: reconhecimento do
comportamento do site, discussão de abordagens, escrita de código e testes, revisão e
documentação. As decisões técnicas descritas acima foram tomadas e revisadas por mim, e o
resultado registrado em `artifacts/` vem de execução real, validada nos dois modos.

## Limitações

- Depende do site estar no ar; o carregamento inicial ocasionalmente estoura o tempo
  limite, tratado com uma segunda tentativa de acesso.
- Se o RPA Challenge traduzir os rótulos (o site tem seletor de idioma), o mapeamento
  precisa do vocabulário do novo idioma em `ROTULOS`.
- O teste de ponta a ponta é a própria execução: não há teste automatizado que suba o
  navegador, para manter a suíte rápida e determinística.
