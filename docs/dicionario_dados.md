# 📖 Dicionário de Dados – Camada MART

Este documento descreve a estrutura do modelo dimensional (Star Schema) gerado para a análise de veículos e envolvidos em acidentes.

---

## 🏗️ 1. Tabela: `fato_acidentes_veiculos`
* **Granularidade:** Um registro por envolvido/veículo associado a um determinado acidente.

### 📋 Colunas
| Nome da Coluna | Tipo | Chave | Descrição |
| :--- | :--- | :---: | :--- |
| `id_acidente_original` | BIGINT / VARCHAR | - | Identificador único do acidente herdado da fonte original. |
| `id_veiculo_original` | BIGINT / VARCHAR | - | Identificador único do veículo envolvido herdado da fonte. |
| `id_data` | DATE | FK | Chave estrangeira que conecta com a tabela `dim_calendario`. |
| `id_localidade` | VARCHAR (MD5) | FK | Chave substituta (Surrogate Key) para a tabela `dim_localidade`. |
| `id_envolvido` | VARCHAR (MD5) | FK | Chave substituta (Surrogate Key) para a tabela `dim_envolvido`. |
| `qtd_registros_envolvidos`| INTEGER | - | Contador básico unitário para registros de participantes. |
| `total_veiculos_no_acidente`| INTEGER | - | KPI 1: Quantidade total de veículos distintos que participaram daquele mesmo acidente. |

### 📊 Propriedades das Métricas e KPIs
* **`qtd_registros_envolvidos`**
  * **Aditividade:** Totalmente Aditiva (pode ser somada livremente por tempo ou região).
* **`total_veiculos_no_acidente` (KPI 1)**
  * **Aditividade:** Não-Aditiva. Como o valor se repete para múltiplos envolvidos no mesmo acidente, a sua soma direta gerará duplicidade. Deve ser analisada por médias ou valores máximos por grupo de acidente.
  * **Fórmula SQL:** `COUNT(DISTINCT id_veiculo) OVER(PARTITION BY id)`

---

## 📅 2. Tabela: `dim_calendario`
* **Granularidade:** Um registro por dia civil.

### 📋 Colunas
| Nome da Coluna | Tipo | Chave | Descrição |
| :--- | :--- | :---: | :--- |
| `id_data` | DATE | PK | Chave primária identificadora da data (Formato: YYYY-MM-DD). |
| `data_completa` | TIMESTAMP | - | Timestamp completo correspondente ao dia. |
| `ano` | INTEGER | - | Ano civil correspondente (ex: 2024). |
| `mes` | INTEGER | - | Número do mês civil (1 a 12). |
| `mes_ano` | VARCHAR | - | Formatação textual para agrupamento mensal (ex: "06/2026"). |
| `trimestre` | INTEGER | - | Trimestre correspondente do ano (1 a 4). |
| `dia_da_semana` | INTEGER | - | Índice numérico do dia da semana (0 para Domingo, 6 para Sábado). |
| `nome_dia_semana` | VARCHAR | - | Nome por extenso do dia da semana em português (ex: "Segunda-feira"). |

---

## 📍 3. Tabela: `dim_localidade`
* **Granularidade:** Um registro por Unidade Federativa (UF) distinta identificada.

### 📋 Colunas
| Nome da Coluna | Tipo | Chave | Descrição |
| :--- | :--- | :---: | :--- |
| `id_localidade` | VARCHAR (MD5) | PK | Chave primária gerada por Hash MD5 baseado na UF. |
| `uf` | VARCHAR | - | Sigla da Unidade Federativa (ex: "MA", "SP"). |

---

## 👥 4. Tabela: `dim_envolvido`
* **Granularidade:** Um registro por categoria de envolvimento mapeada.

### 📋 Colunas
| Nome da Coluna | Tipo | Chave | Descrição |
| :--- | :--- | :---: | :--- |
| `id_envolvido` | VARCHAR (MD5) | PK | Chave primária gerada por Hash MD5 baseado na descrição do envolvido. |
| `tipo_envolvido` | VARCHAR | - | Papel do indivíduo na ocorrência (ex: "Condutor", "Passageiro", "Pedestre"). |

---

## 👁️ 5. View Analítica: `v_kpi_envolvidos_por_uf` (KPI 2)
* **Descrição:** Agregação calculada que consolida o volume geográfico total de impactos.
* **Fórmula:** `SELECT uf, COUNT(id_acidente_original) AS total_acidentes, SUM(qtd_registros_envolvidos) AS total_envolvidos_afetados FROM ... GROUP BY uf`
* **Unidade de Medida:** Contagem absoluta de Acidentes e Indivíduos Afetados.