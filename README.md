# Mapeamento e Análise Espacial de Acidentes em Rodovias Federais (PRF)

## 📌 DESCRIÇÃO

<div align="justify">
Este repositório contém o projeto prático desenvolvido para a disciplina de Introdução à Ciência de Dados do curso de Mestrado em Computação Aplicada. O objetivo principal é aplicar técnicas de análise espacial e visualização de dados para investigar padrões de ocorrências em rodovias federais brasileiras.
O projeto utiliza a base de dados abertos da Polícia Rodoviária Federal (PRF) (https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf), escolhida pela sua expressiva riqueza de variáveis físicas, temporais e geográficas (latitude e longitude nativas). O foco analítico principal deste estudo está no recorte regional do estado do Maranhão, buscando extrair <i>insights</i> sobre a dinâmica dos acidentes de trânsito na região.
</div>

## 🛠 Pré-requisitos

<div align="justify">
Para gerenciar as dependências e o ambiente virtual deste projeto de forma performática, utilizamos o <b>uv</b>, um instalador e gerenciador de pacotes Python extremamente rápido escrito em Rust.
</div>

### Instalação do uv

**No macOS e Linux:**

```bash
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
```

**No Windows/PowerShell:**

```bash
powershell -c "irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex"
```

**Para outras formas de instalação, consulte a documentação oficial do uv:** (https://docs.astral.sh/uv/getting-started/installation/)

## 🚀 Como executar

1. Para baixar do repositório: git clone (https://github.com/danzz32/data-science-project.git)

2. Para sincronizar as dependências do projeto: uv sync

3. Para executar o script dentro do ambiente virtual isolado: uv run python src/ingest.py

## 🔐 Variáveis de Ambiente


## 📈 Resultado Esperado

<div align="justify">
Ao final da execução deste projeto, espera-se a geração de:

1.	Mapas de Calor Interativos: Visualizações geográficas que identifiquem os trechos de rodovias com maior densidade de acidentes (hotspots).

2.	Análise de Periculosidade: Identificação estatística dos fatores que mais contribuem para a gravidade das ocorrências (ex: relação entre condições climáticas e óbitos).

3.	Séries Temporais: Gráficos que demonstrem os períodos de maior vulnerabilidade (feriados, horários de pico ou sazonalidade mensal).

4.	Relatório Consolidado: Um conjunto de insights que correlacionam a infraestrutura viária do estado com o comportamento dos sinistros registrados pela PRF.
<div>
