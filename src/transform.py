import pandas as pd
import numpy as np
from pathlib import Path
import logging

# Configuração básica de log para acompanhar a execução
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_latest_raw_file(raw_dir: Path) -> Path:
    """Busca o ficheiro CSV mais recente na pasta raw."""
    arquivos = list(raw_dir.glob("prf_191_*.csv"))
    if not arquivos:
        raise FileNotFoundError("Nenhum ficheiro bruto encontrado na pasta data/raw/")
    return max(arquivos, key=lambda p: p.stat().st_mtime)

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica as regras de limpeza baseadas nas 4 dimensões de qualidade."""
    df_clean = df.copy()
    
    # 1. TEMPORALIDADE: Converter datas e remover inconsistências temporais
    logging.info("A aplicar regras de Temporalidade...")
    if 'data_inversa' in df_clean.columns:
        df_clean['data_inversa'] = pd.to_datetime(df_clean['data_inversa'], errors='coerce', dayfirst=True)
        df_clean = df_clean.dropna(subset=['data_inversa'])
        df_clean = df_clean[df_clean['data_inversa'] <= pd.Timestamp.now()]
        
    # 2. ACURÁCIA: Filtrar domínios válidos e corrigir tipos
    logging.info("A aplicar regras de Acurácia...")
    if 'uf' in df_clean.columns:
        ufs_validas = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
                       'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN',
                       'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']
        df_clean = df_clean[df_clean['uf'].isin(ufs_validas)]
        
    cols_str = df_clean.select_dtypes(include=['object']).columns
    for col in cols_str:
        df_clean[col] = df_clean[col].astype(str).str.strip().str.lower()

    # 3. CONSISTÊNCIA: Corrigir contradições lógicas
    logging.info("A aplicar regras de Consistência...")
    colunas_vitimas = ['mortos', 'feridos_leves', 'feridos_graves', 'veiculos']
    if all(c in df_clean.columns for c in colunas_vitimas):
        for col in colunas_vitimas:
            df_clean[col] = df_clean[col].abs()
            
        mascara_inconsistente = (df_clean['veiculos'] == 0) & ((df_clean['mortos'] > 0) | (df_clean['feridos_leves'] > 0))
        df_clean = df_clean[~mascara_inconsistente]

    # 4. COMPLETUDE: Lidar com nulos em campos críticos
    logging.info("A aplicar regras de Completude...")
    if 'municipio' in df_clean.columns:
        df_clean = df_clean.dropna(subset=['municipio'])
        df_clean[cols_str] = df_clean[cols_str].replace(['nan', 'none', ''], 'nao_informado')
        df_clean[cols_str] = df_clean[cols_str].fillna('nao_informado')

    return df_clean

def main():
    # Configuração de caminhos mudando para a camada TRUSTED
    ROOT_DIR = Path(__file__).resolve().parent.parent
    RAW_DIR = ROOT_DIR / "data" / "raw"
    TRUSTED_DIR = ROOT_DIR / "data" / "trusted"
    
    # Cria a pasta trusted se ela não existir
    TRUSTED_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        raw_file = get_latest_raw_file(RAW_DIR)
        logging.info(f"A iniciar processamento do ficheiro: {raw_file.name}")
        
        # Leitura dos dados brutos (CSV)
        df_raw = pd.read_csv(raw_file, sep=';', encoding='latin-1', low_memory=False)
        
        # Obtém o tamanho do ficheiro CSV original em MB
        raw_size_mb = raw_file.stat().st_size / (1024 * 1024)
        logging.info(f"Tamanho do ficheiro bruto (CSV): {raw_size_mb:.2f} MB")
        logging.info(f"Linhas antes da limpeza: {len(df_raw)}")
        
        # Transformação e Limpeza
        df_processed = clean_data(df_raw)
        logging.info(f"Linhas após limpeza: {len(df_processed)}")
        
        # O formato de saída agora é PARQUET
        output_path = TRUSTED_DIR / "prf_acidentes_trusted.parquet"
        df_processed.to_parquet(output_path, index=False)
        
        # Obtém o tamanho do ficheiro Parquet final em MB
        trusted_size_mb = output_path.stat().st_size / (1024 * 1024)
        
        logging.info(f"✅ Dados limpos guardados com sucesso no formato PARQUET em: {output_path}")
        logging.info(f"📊 Tamanho do ficheiro processado (Parquet): {trusted_size_mb:.2f} MB")
        
        # Opcional: Calcular a percentagem de redução de tamanho
        reducao = ((raw_size_mb - trusted_size_mb) / raw_size_mb) * 100
        logging.info(f"📉 Redução de espaço em disco: {reducao:.1f}%")
        
    except Exception as e:
        logging.error(f"❌ Erro durante a transformação: {e}")

if __name__ == "__main__":
    main()