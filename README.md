# Mapeamento e Análise Espacial de Acidentes em Rodovias Federais (PRF)

## 📌 DESCRIÇÃO

<div align="justify">
Este repositório contém o projeto prático desenvolvido para a disciplina de Introdução à Ciência de Dados do curso de Mestrado em Computação Aplicada. O objetivo principal é aplicar técnicas de análise espacial e visualização de dados para investigar padrões de ocorrências em rodovias federais brasileiras.

O projeto utiliza a base de dados abertos da Polícia Rodoviária Federal (PRF) (https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf), escolhida pela sua expressiva riqueza de variáveis físicas, temporais e geográficas (latitude e longitude nativas).

O foco analítico principal deste estudo está no recorte regional do estado do Maranhão, buscando extrair insights sobre a dinâmica dos acidentes de trânsito na região.
</div>

---

# 🛠 Pré-requisitos

- Python 3.12+
- uv (gerenciador de pacotes Python)
- Jupyter (execução de notebooks)
- Quarto (renderização de relatórios `.qmd`)
- Git

---

# ⚙️ Configuração do Ambiente

### 1. Clonar o repositório

```bash
git clone https://github.com/danzz32/data-science-project.git
cd data-science-project
```

### 2. Criar e ativar o ambiente virtual

```bash
uv venv
source .venv/bin/activate  # Linux/macOS
# ou
.venv\Scripts\activate  # Windows
```

### 3. Instalar dependências

```bash
uv sync
```

### 4. Configurar Jupyter (opcional)

```bash
uv pip install jupyter ipykernel notebook
uv run python -m ipykernel install --user --name=data-science-project
```

---

# 🔐 Variáveis de Ambiente

O gerenciamento de configurações é feito através de variáveis de ambiente. Para configurar seu ambiente:

```bash
cp .env.example .env
```

Para a etapa inicial de ingestão (download dos dados públicos da PRF), nenhuma variável de ambiente ou chave de API é necessária.

---

# ▶️ Execução do Projeto

### 1. Executar a Ingestão (Camada Raw)

```bash
uv run src/ingest.py
```

A camada Raw armazena os dados em sua forma original, íntegra e imutável, servindo como fonte de verdade para todas as transformações posteriores.

### 2. Executar o Pipeline de Qualidade e Transformação (Camada Trusted)

```bash
uv run src/transform.py
```

A camada Trusted contém os dados após validação de qualidade, tratamento de inconsistências e transformações estruturais necessárias para análise.

### 3. Executar Relatórios Quarto (.qmd)

Os relatórios podem ser executados no VS Code ou via terminal:

```bash
quarto render relatorio.qmd
```

---

# 📈 Resultado Esperado

<div align="justify">
Ao final da execução deste projeto, espera-se a geração de:

1. **Mapas de Calor Interativos**: Visualizações geográficas que identifiquem os trechos de rodovias com maior densidade de acidentes (hotspots).

2. **Análise de Periculosidade**: Identificação estatística dos fatores que mais contribuem para a gravidade das ocorrências (ex: relação entre condições climáticas e óbitos).

3. **Séries Temporais**: Gráficos que demonstrem os períodos de maior vulnerabilidade (feriados, horários de pico ou sazonalidade mensal).

4. **Relatório Consolidado**: Um conjunto de insights que correlacionam a infraestrutura viária do estado com o comportamento dos sinistros registrados pela PRF.
</div>

---

# 📁 Estrutura do Projeto

```
data-science-project/
├── src/
│   ├── ingest.py          # Ingestão de dados (camada Raw)
│   ├── transform.py       # Transformação de dados (camada Trusted)
│   └── ...
├── docs/             # Análises exploratórias
├── reports/               # Relatórios Quarto (.qmd)
├── schemas/
├── data/
│   ├── raw/              # Dados brutos (imutáveis)
│   ├── trusted/          # Dados transformados e validados
│   └── processed/        # Dados para análise final
├── .env.example
└── pyproject.toml         # Dependências do projeto
```

---

# 📚 Referências

- Dados abertos PRF: https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf
- Documentação uv: https://docs.astral.sh/uv/
- Documentação Quarto: https://quarto.org/