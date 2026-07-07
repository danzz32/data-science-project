# Mapeamento e Análise Espacial de Acidentes em Rodovias Federais (PRF)

## 📌 DESCRIÇÃO

<div align="justify">
Este repositório contém o projeto prático desenvolvido para a disciplina de Introdução à Ciência de Dados do curso de Mestrado em Computação Aplicada. O objetivo principal é aplicar técnicas de análise espacial e visualização de dados para investigar padrões de ocorrências em rodovias federais brasileiras.

O projeto utiliza a base de dados abertos da Polícia Rodoviária Federal (PRF) (https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf), escolhida pela sua expressiva riqueza de variáveis físicas, temporais e geográficas (latitude e longitude nativas).

O foco analítico principal deste estudo está no recorte regional do estado do Maranhão, buscando extrair insights sobre a dinâmica dos acidentes de trânsito na região.
</div>

---

## 🧱 MODELO DIMENSIONAL

<div align="justify">
A camada final do pipeline (Mart), construída em <code>src/build_mart.py</code> com <b>DuckDB</b>, organiza os dados da camada Trusted em um <b>modelo dimensional em esquema estrela (star schema)</b>, persistido em arquivos Parquet na pasta <code>data/mart/</code>.
</div>

**Tabela fato:**

| Tabela | Descrição |
|---|---|
| `fato_acidentes_veiculos` | Grão: um registro por veículo envolvido em um acidente. Contém `id_acidente_original`, `id_veiculo_original`, as chaves estrangeiras para as dimensões (`id_data_fato`, `id_localidade`, `id_envolvido`) e as métricas `qtd_registros_envolvidos` e `total_veiculos_no_acidente` (calculada via window function, particionada por acidente). |

**Tabelas dimensão:**

| Dimensão | Descrição |
|---|---|
| `dim_calendario` | Dimensão calendário gerada programaticamente (2021–2025), independente da fonte original, com `id_data`, `data_completa`, `ano`, `mes`, `mes_ano`, `trimestre`, `dia_da_semana` e `nome_dia_semana`. |
| `dim_localidade` | Unidades Federativas (`uf`) distintas, com chave `id_localidade` gerada via hash MD5. |
| `dim_envolvido` | Tipos de envolvido (`tipo_envolvido`) distintos, com chave `id_envolvido` gerada via hash MD5. |

> ⚠️ **Nota sobre a dimensão calendário:** como a camada Trusted não possui uma coluna de data original confiável para o relacionamento, `id_data_fato` é atribuído de forma sequencial/cíclica (via `ROW_NUMBER()` sobre uma janela de 1825 dias) e não representa a data real do acidente. Essa limitação deve ser tratada em uma próxima iteração do pipeline (ex.: recuperar a data original da fonte PRF).

> ℹ️ **Colunas adicionais consumidas pelo dashboard:** desde a Sprint 4, `fato_acidentes_veiculos` também expõe `br` / `rodovia_original` (rodovia), `latitude`/`longitude` (herdadas para a tabela fato para permitir mapas sem join adicional) e `is_fatal` (flag de óbito), e `dim_localidade` expõe `latitude`/`longitude`. Esses campos são gerados em `src/build_mart.py` e consumidos pelo `app.py` nas visualizações de severidade, mapas e ranking de rodovias. O dicionário de dados em [`docs/dicionario_dados.md`](./docs/dicionario_dados.md) ainda descreve apenas o esquema da Sprint 3 e deve ser atualizado para incluir essas colunas.

**View analítica:**

- `v_kpi_envolvidos_por_uf` — agregação de `fato_acidentes_veiculos` por UF, com total de acidentes e total de envolvidos afetados.

> 📎 Detalhamento completo de cada coluna, tipo de dado e regra de derivação está disponível no **dicionário de dados** (ver seção [Dicionário de Dados](#-dicionário-de-dados)).

---

## 🛠 Pré-requisitos

- Python 3.12+
- uv (gerenciador de pacotes Python)
- Jupyter (execução de notebooks)
- Quarto (renderização de relatórios `.qmd`)
- Git
- Visual Studio Code (recomendado)

---

## ⚙️ Configuração do Ambiente de Desenvolvimento

### 🐍 Instalação do Python

Verifique se o Python já está instalado:

```bash
python --version
# ou
py --version
```

Caso não esteja instalado:

- Windows: https://www.python.org/downloads/windows/
- Linux/macOS: utilizar o gerenciador de pacotes da distribuição.

### ⚡ Instalação do uv

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux/macOS:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verificar instalação:

```bash
uv --version
```

### 📥 Clonar o repositório

```bash
git clone https://github.com/danzz32/data-science-project.git
cd data-science-project
```

### 📦 Criar e ativar o ambiente virtual

```bash
uv venv
source .venv/bin/activate  # Linux/macOS
# ou
.venv\Scripts\activate     # Windows (PowerShell)
```

> Caso o PowerShell bloqueie a execução do script de ativação:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

### 📚 Instalar dependências

```bash
uv sync
```

> As bibliotecas usadas pelo dashboard interativo (`streamlit`, `streamlit-shadcn-ui`, `duckdb`, `pandas` e `plotly`) já fazem parte das dependências declaradas em `pyproject.toml` e são instaladas junto com o restante do projeto por esse mesmo comando.

### 📓 Configurar Jupyter (opcional)

```bash
uv pip install jupyter ipykernel notebook
uv run python -m ipykernel install --user --name=data-science-project
```

### 📝 Instalar Quarto

O Quarto é utilizado para execução e renderização dos relatórios `.qmd`.

**Windows (PowerShell):**
```powershell
winget install --id Posit.Quarto -e
```

**Ubuntu/Debian:**
```bash
sudo apt install quarto
```

**Fedora:**
```bash
sudo dnf install quarto
```

**macOS:**
```bash
brew install quarto
```

Verificar instalação:

```bash
quarto --version
```

### 🧩 Extensões recomendadas do VS Code

| Extensão | Finalidade |
|---|---|
| Python (Microsoft) | Suporte Python |
| Jupyter | Execução de notebooks |
| Quarto | Execução e renderização `.qmd` |

---

## 🔐 Variáveis de Ambiente

<div align="justify">
O gerenciamento de configurações é feito através de variáveis de ambiente. Para configurar seu ambiente, faça uma cópia do arquivo de exemplo:
</div>

```bash
cp .env.example .env
```

Para a etapa inicial de ingestão (download dos dados públicos da PRF), nenhuma variável de ambiente ou chave de API é necessária. O script funciona apenas com as configurações padrão.

---

## ▶️ Execução do Projeto

### 1. Ingestão (Camada Raw)

```bash
uv run python src/ingest.py
```

A camada Raw armazena os dados em sua forma original, íntegra e imutável, servindo como fonte de verdade para todas as transformações posteriores.

### 2. Qualidade e Transformação (Camada Trusted)

```bash
uv run python src/transform.py
```

A camada Trusted contém os dados após validação de qualidade, tratamento de inconsistências e transformações estruturais necessárias para análise.

### 3. Construção do Modelo Dimensional (Camada Mart)

```bash
uv run python src/build_mart.py
```

Etapa responsável por estruturar os dados da camada Trusted no modelo dimensional (fato + dimensões) descrito na seção [Modelo Dimensional](#-modelo-dimensional), utilizando DuckDB. As tabelas (`dim_calendario`, `dim_localidade`, `dim_envolvido` e `fato_acidentes_veiculos`) são persistidas em formato Parquet em `data/mart/`, e um resumo de volumetria (quantidade de linhas por tabela) é impresso ao final da execução.

### 4. Dashboard Interativo (Streamlit)

```bash
uv run streamlit run app.py
```

O comando sobe o dashboard em `http://localhost:8501`. A aplicação lê diretamente os arquivos Parquet da camada Mart (`data/mart/`) através de consultas DuckDB — portanto, é necessário ter executado a etapa anterior (Camada Mart) pelo menos uma vez antes de abrir o dashboard.

O painel está organizado em:

- **Filtros no topo** — Ano, Região, UF e critério de ranking de rodovias (maior/menor índice de acidentes), todos combináveis entre si.
- **Cartões de indicadores (KPIs)** — Acidentes, Acidentes Fatais, Envolvidos, Índice de Letalidade e Registros Veículo-Envolvido, recalculados dinamicamente conforme os filtros aplicados.
- **📍 Análise Geográfica & Rodovias** — volumetria de envolvidos por UF, mapa de dispersão geográfico das ocorrências e ranking Top 5 de rodovias federais.
- **🪖 Perfil de Risco & Severidade** — distribuição de severidade (fatal x não fatal) por papel do envolvido, mapa de densidade de acidentes fatais e ranking das rodovias mais críticas.
- **📅 Sazonalidade Temporal** — evolução mensal de ocorrências por ano (com rótulos de dados) e comparativo sobreposto entre os anos selecionados.

### 5. Notebooks de Análise Exploratória

Os notebooks de análise exploratória ficam em [`docs/`](./docs) e podem ser executados via VS Code/Jupyter selecionando o kernel:

```bash
uv run jupyter notebook docs/
```

No VS Code: abra o arquivo `.ipynb`, clique em **Select Kernel** e escolha `data-science-project` (ou o interpretador da pasta `.venv`).

### 6. Relatórios Quarto (.qmd)

Os notebooks exploratórios (`docs/eda_qualidade.qmd`, `docs/eda_modelagem.qmd`) e o relatório executivo (`relatorio-executivo.qmd`, na raiz do projeto) podem ser renderizados via VS Code ou terminal:

```bash
quarto render docs/eda_qualidade.qmd --output-dir ../reports
quarto render docs/eda_modelagem.qmd --output-dir ../reports
quarto render relatorio-executivo.qmd
```

Todos geram HTML em [`reports/`](./reports): `eda_qualidade.html`, `eda_modelagem.html` e `relatorio-executivo.html`. Este último é o **relatório executivo** pedido na Sprint 4 — dirigido a quem vai decidir, não a quem vai auditar o pipeline. Ele responde a perguntas analíticas com narrativa Contexto → Dados → Conclusão, reaproveitando consultas e visualizações da Sprint 3, mas com texto escrito para um público não técnico. O HTML já vem commitado em `reports/relatorio-executivo.html`, então não é necessário rodar `quarto render` para lê-lo — apenas para gerá-lo novamente após alguma mudança.

---

## 📈 Resultado Esperado

<div align="justify">
Ao final da execução deste projeto, espera-se a geração de:

1. **Mapas de Calor Interativos**: Visualizações geográficas que identifiquem os trechos de rodovias com maior densidade de acidentes (hotspots).
2. **Análise de Periculosidade**: Identificação estatística dos fatores que mais contribuem para a gravidade das ocorrências (ex: relação entre condições climáticas e óbitos).
3. **Séries Temporais**: Gráficos que demonstrem os períodos de maior vulnerabilidade (feriados, horários de pico ou sazonalidade mensal).
4. **Relatório Consolidado**: Um conjunto de insights que correlacionam a infraestrutura viária do estado com o comportamento dos sinistros registrados pela PRF.
5. **Dashboard Interativo**: Uma aplicação Streamlit que consolida os KPIs, mapas e séries temporais acima em um painel único, navegável por filtros de ano, região e UF, voltado a uma leitura executiva dos dados da Mart.
</div>

---

## 📖 Dicionário de Dados

O dicionário de dados, com a descrição de cada coluna, tipo, domínio e regra de derivação das tabelas fato e dimensão, está disponível em [`docs/dicionario_dados.md`](./docs/dicionario_dados.md).

---

## 📁 Estrutura do Projeto

```
data-science-project/
├── src/
│   ├── ingest.py           # Ingestão de dados (camada Raw)
│   ├── transform.py        # Transformação de dados (camada Trusted)
│   ├── build_mart.py       # Construção do modelo dimensional (camada Mart)
│   └── ...
├── app.py                  # Dashboard interativo (Streamlit + DuckDB + Plotly)
├── relatorio-executivo.qmd # Fonte do relatório executivo (Sprint 4)
├── docs/                   # Notebooks de análise exploratória (.qmd) + dicionário de dados
├── reports/                # Saída renderizada (.html) de todos os relatórios Quarto
├── schemas/                # Reservado para versionamento futuro de schemas formais
├── data/
│   ├── raw/                # Dados brutos (imutáveis)
│   ├── trusted/            # Dados transformados e validados
│   └── mart/               # Modelo dimensional (fato + dimensões), Parquet
├── .env.example
└── pyproject.toml          # Dependências do projeto
```

---

## 📚 Referências

- Dados abertos PRF: https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf
- Documentação uv: https://docs.astral.sh/uv/
- Documentação Quarto: https://quarto.org/