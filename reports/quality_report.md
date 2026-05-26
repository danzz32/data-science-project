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
