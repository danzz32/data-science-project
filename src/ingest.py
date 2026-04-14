import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import kagglehub
from kagglehub import KaggleDatasetAdapter
# from .autonotebook import tqdm as notebook_tqdm
import os
import shutil

# 1. Configuração de Caminhos
PROJECT_ROOT = Path.cwd().parent 
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_FILE_PATH = RAW_DIR / "911.csv"

# Garante que a pasta de destino exista
RAW_DIR.mkdir(parents=True, exist_ok=True)

if RAW_FILE_PATH.exists():
    print(f"✅ Arquivo já existe em {RAW_FILE_PATH}. Carregando...")
    df = pd.read_csv(RAW_FILE_PATH, sep=None, engine='python', encoding='utf-8')
else:
    print("⏳ Iniciando download e organização dos arquivos...")
    try:
        # 2. Download para o cache do sistema
        download_path = kagglehub.dataset_download("ahmadrafiee/911-calls-for-service-metadata-1-million-record")
        
        # 3. Localiza o arquivo CSV no cache
        files = [f for f in os.listdir(download_path) if f.endswith('.csv')]
        if not files:
            raise FileNotFoundError("Nenhum CSV encontrado no download.")
        
        temp_csv_path = Path(download_path) / files[0]

        # 4. Move o arquivo do cache para a sua pasta data/raw/
        shutil.copy(temp_csv_path, RAW_FILE_PATH)
        print(f"📂 Arquivo movido com sucesso para: {RAW_FILE_PATH}")

        # 5. Leitura com detecção automática de separador
        df = pd.read_csv(RAW_FILE_PATH, sep=None, engine='python', on_bad_lines='warn')
        
        print(f"🎯 Dados carregados com sucesso! Total de linhas: {len(df)}")

    except Exception as e:
        print(f"❌ Erro: {e}")

if 'df' in locals():
    print(df.head())