<<<<<<< HEAD
# Relatório de Qualidade de Dados - Camada Trusted
**Data de Execução:** 2026-05-26 00:31:36
**Estratégia Adotada:** Quarentena Seletiva + Correção Automática de Formatos

## Resumo da Execução (Linhas)
* **Total de Registos Lidos (Raw):** 342624
* **Total Aprovados na Validação:** 342624
* **Total Enviados para Quarentena:** 0

## Correções Automáticas Aplicadas (Dados Salvos do Descarte) ✔️
* **Formatos de Data Corrigidos (Invertidos para Padrão):** 342624 registos salvos
* **Contradições Vitimológicas Ajustadas (Morto & Ileso):** 13389 registos salvos

## Eficiência de Armazenamento (CSV vs Parquet)
* **Tamanho do Ficheiro Original (CSV):** 85.37 MB
* **Tamanho do Ficheiro Destino (Parquet Trusted):** 13.44 MB
* **Percentual de Redução de Espaço:** **84.26%** de economia em disco 📉

## Motivos de Quarentena por Categoria (Erros Críticos)
* **Duplicatas Exatas:** 0 registos
* **Temporalidade (Datas totalmente corrompidas/ilegíveis):** 0 registos
* **Acurácia (UF inválida):** 0 registos
* **Consistência (Dados contraditórios irrecuperáveis):** 0 registos
* **Completude (Município nulo):** 0 registos
=======
# Relatório de Qualidade de Dados - Camada Trusted (DuckDB Motor)
**Data de Execução:** 2026-06-21 11:41:07
**Estratégia Computacional:** Arquitetura Vetorizada de Alta Performance com DuckDB

## Resumo da Execução (Linhas)
* **Total de Registros Lidos (Layer Raw):** 2,702,004
* **Total Aprovados pelo Pipeline:** 2,702,004
* **Total Isolados na Quarentena:** 0

## Eficiência de Armazenamento e Compressão 📉
* **Tamanho do Arquivo Bruto (CSV):** 986.75 MB
* **Tamanho do Arquivo Otimizado (Parquet Trusted):** 31.53 MB
* **Ganho de Economia em Disco:** **96.80%** reduzidos com codificação Parquet e Compressão Snappy

## Detalhamento de Erros de Quarentena
* **Falhas Críticas de Parsing (ID ou Data Nula):** 0 registros
>>>>>>> 0dd1dc22f33a32648db475cb4785a79ef073fed3
