# Relatório de Qualidade de Dados - Camada Trusted
**Data de Execução:** 2026-05-24 19:47:48
**Estratégia Adotada:** Quarentena (Isolamento de registos inválidos)

## Resumo da Execução
* **Total de Registos Lidos (Raw):** 2702004
* **Total Aprovados na Validação:** 1079742
* **Total Enviados para Quarentena:** 1622262

## Motivos de Quarentena por Categoria
* **Duplicatas Exatas:** 0 registos
* **Temporalidade (Datas inválidas ou no futuro):** 1622262 registos
* **Acurácia (UF inválida):** 0 registos
* **Consistência (Dados vitimológicos contraditórios):** 0 registos
* **Completude (Município nulo):** 0 registos

*Nota: Os registos quarentenados foram isolados no ficheiro `prf_acidentes_quarentena.parquet` na camada `data/quarantine/` para futura auditoria.*
