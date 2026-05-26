# Mapeamento e Análise Espacial de Acidentes em Rodovias Federais (PRF)

## 📌 DESCRIÇÃO

<div align="justify">
Este repositório contém o projeto prático desenvolvido para a disciplina de Introdução à Ciência de Dados do curso de Mestrado em Computação Aplicada. O objetivo principal é aplicar técnicas de análise espacial e visualização de dados para investigar padrões de ocorrências em rodovias federais brasileiras.

O projeto utiliza a base de dados abertos da Polícia Rodoviária Federal (PRF) (https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf), escolhida pela sua expressiva riqueza de variáveis físicas, temporais e geográficas (latitude e longitude nativas).

O foco analítico principal deste estudo está no recorte regional do estado do Maranhão, buscando extrair insights sobre a dinâmica dos acidentes de trânsito na região.
</div>

---

# 🛠 Pré-requisitos

<div align="justify">
Para gerenciamento do ambiente virtual e dependências, este projeto utiliza o <b>uv</b>, um gerenciador de pacotes Python extremamente rápido desenvolvido em Rust.

Além disso, para execução de notebooks e relatórios analíticos, utilizamos:
</div>

- Python 3.12+
- Jupyter
- Quarto
- Visual Studio Code (recomendado)

---

# ⚙️ Configuração do Ambiente de Desenvolvimento

## 🐍 Instalação do Python

Verifique se o Python já está instalado:

```bash
python --version
```

ou:

```bash
py --version
```

Caso não esteja instalado:

- Windows: https://www.python.org/downloads/windows/
- Linux/macOS: utilizar o gerenciador de pacotes da distribuição.

---

# ⚡ Instalação do uv

## Windows (PowerShell)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Linux/macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Verificar instalação

```bash
uv --version
```

---

# 📥 Clonar o Repositório

```bash
git clone https://github.com/danzz32/data-science-project.git
```

Entrar na pasta:

```bash
cd data-science-project
```

---

# 📦 Criação do Ambiente Virtual

```bash
uv venv
```

---

# ▶️ Ativação do Ambiente Virtual

## Windows (PowerShell)

Caso o PowerShell bloqueie scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Depois ative o ambiente:

```powershell
.venv\Scripts\activate
```

## Linux/macOS

```bash
source .venv/bin/activate
```

---

# 📚 Instalação das Dependências

Instalar todas as dependências do projeto:

```bash
uv sync
```

---

# 📓 Instalação do Jupyter

## Instalar Jupyter e Kernel Python

```bash
uv pip install jupyter ipykernel notebook
```

## Registrar Kernel do Projeto

```bash
uv run python -m ipykernel install --user --name=data-science-project
```

Após isso, o kernel poderá ser selecionado no VS Code/Jupyter.

---

# 📝 Instalação do Quarto

O Quarto é utilizado para execução e renderização dos relatórios `.qmd`.

## Windows (PowerShell)

```powershell
winget install --id Posit.Quarto -e
```

## Linux

### Ubuntu/Debian

```bash
sudo apt install quarto
```

### Fedora

```bash
sudo dnf install quarto
```

## macOS

```bash
brew install quarto
```

## Verificar instalação

```bash
quarto --version
```

---

# 🧩 Extensões Recomendadas do VS Code

Instale as seguintes extensões:

| Extensão | Finalidade |
|---|---|
| Python (Microsoft) | Suporte Python |
| Jupyter | Execução de notebooks |
| Quarto | Execução e renderização `.qmd` |

---

# ▶️ Configuração do Kernel no VS Code

1. Abra o projeto no VS Code
2. Abra um arquivo `.ipynb` ou `.qmd`
3. Clique em `Select Kernel`
4. Escolha:
   - `data-science-project`
   - ou o interpretador Python da pasta `.venv`

---

# 📄 Execução de Relatórios Quarto (.qmd)

Exemplo de bloco executável:

````markdown
```{python}
print("Olá mundo")
```

## 🚀 Como executar

1. Para baixar do repositório:
```bash
   git clone https://github.com/danzz32/data-science-project.git
```
2. Para sincronizar as dependências do projeto:
```bash
   uv syncgit branch
```
3. Executar a Ingestão (Camada Raw):
```bash
   uv run src/ingest.py
```
4. Executar o Pipeline de Qualidade e Transformação (Camada Trusted):
```bash
uv run python src/transform.py
```
## 🔐 Variáveis de Ambiente
<div align="justify">
O gerenciamento de configurações e credenciais locais é feito através de variáveis de ambiente. Este projeto inclui um arquivo de modelo para facilitar essa configuração.
Para configurar o seu ambiente, faça uma cópia do arquivo de exemplo executando o comando abaixo no seu terminal:
</div>

```bash
cp .env.example .env
```
<div align="justify">
Em seguida, abra o arquivo .env recém-criado na raiz do projeto e preencha as informações (se necessário).
Variáveis utilizadas no projeto:
Nesta etapa inicial de ingestão (download dos dados públicos da PRF), nenhuma variável de ambiente ou chave de API foi necessária. O script funcionará perfeitamente apenas com as configurações padrão.
</div>

## 📈 Resultado Esperado

<div align="justify">
Ao final da execução deste projeto, espera-se a geração de:

1.	Mapas de Calor Interativos: Visualizações geográficas que identifiquem os trechos de rodovias com maior densidade de acidentes (hotspots).

2.	Análise de Periculosidade: Identificação estatística dos fatores que mais contribuem para a gravidade das ocorrências (ex: relação entre condições climáticas e óbitos).

3.	Séries Temporais: Gráficos que demonstrem os períodos de maior vulnerabilidade (feriados, horários de pico ou sazonalidade mensal).

4.	Relatório Consolidado: Um conjunto de insights que correlacionam a infraestrutura viária do estado com o comportamento dos sinistros registrados pela PRF.
<div>
