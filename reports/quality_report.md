# Síntese Executiva: Relatório de Qualidade de Dados (Camada Trusted)

**Período de Referência:** Maio a Junho de 2026
**Arquitetura e Estratégia:** Processamento vetorizado de alta performance (DuckDB) aliado a Quarentena Seletiva e Correção Automática de Formatos.

---

## 📊 1. Resumo Geral de Execução (Volume e Qualidade)

* **Total de Registos Processados (Raw):** 3.044.628 registos
  * *Lote 1 (Maio):* 342.624 registos
  * *Lote 2 (Junho):* 2.702.004 registos
* **Total Aprovados pelo Pipeline:** 3.044.628 registos (**100% de aproveitamento**)
* **Total Isolados na Quarentena:** 0 registos

Com a estratégia aplicada, nenhum registo foi retido por falhas críticas de integridade, como duplicados exatos, problemas graves de temporalidade, inconsistências geográficas (UF inválida) ou chaves nulas (Município/ID).

---

## 🛠️ 2. Engenharia de Dados e Resgate Automático

A aplicação de algoritmos de correção automática salvou milhares de registos do descarte prematuro, aumentando a completude da base tratada:

* **Padronização Temporal:** **342.624 registos corrigidos** através da inversão automática de formatos de data para o padrão do pipeline.
* **Consistência Vitimológica:** **13.389 registos ajustados** devido a contradições lógicas (ex: reconciliação de status simultâneos de "Morto & Ileso").

---

## 📉 3. Eficiência de Armazenamento e Infraestrutura

A transição do modelo bruto em texto plano (CSV) para o formato colunar otimizado (Parquet) com compressão de alta performance (Snappy/DuckDB) gerou ganhos massivos na infraestrutura de disco:

### Métricas Acumuladas
* **Tamanho Total do Ficheiro Bruto (CSV):** 1.072,12 MB (~1,07 GB)
* **Tamanho Total do Ficheiro Otimizado (Parquet Trusted):** 44,97 MB (~45 MB)
* **Percentagem Média de Redução:** **95,81% de economia global** em armazenamento.

### Detalhamento por Lote
* **Lote 1 (Estratégia Tradicional):** Redução de **84,26%** (de 85,37 MB para 13,44 MB).
* **Lote 2 (Motor DuckDB Vetorizado):** Redução de **96,80%** (de 986,75 MB para 31,53 MB) devido à maior eficiência de codificação e compressão Snappy.