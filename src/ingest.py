import os
import shutil
import zipfile
import gdown
import pandas as pd
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

def main():
    # 1. Carrega as variáveis de ambiente do arquivo .env
    load_dotenv()

    # 2. Configurações de Pastas e Data
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    RAW_DIR = PROJECT_ROOT / "data" / "raw"
    TEMP_DIR = RAW_DIR / "temp_extraction" 
    
    # Gerando a data da ingestão
    datestamp = datetime.now().strftime("%Y-%m-%d")
    FINAL_FILE = RAW_DIR / f"prf_acidentes_consolidado_{datestamp}.csv"

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Check de Idempotência (Validador de existência)
    if FINAL_FILE.exists():
        print(f"⚠️  Atenção: O arquivo '{FINAL_FILE.name}' já existe.")
        print("⏭️  Pulando a ingestão para evitar duplicidade e retrabalho de múltiplos anos.")
        return

    # Só cria a pasta temporária se o processo for realmente rodar
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # 4. Mapeamento de Anos e IDs 
    DATA_SOURCES = {
        "2025": "1-PJGRbfSe7PVjU37A3wTCls_NRXyVGRD",
        "2024": "14qBOhrE1gioVtuXgxkCJ9kCA8YtUGXKA",  
        "2023": "1-caam_dahYOf2eorq4mez04Om6DD5d_3", 
        "2022": "1wskEgRC3ame7rncSDQ7qWhKsoKw1lohY",
        "2021": "1Gk3U6cMOZIevsDZHLi6J503xoCRS_lnI",
    }

    all_dataframes = []
    first_header = None

    print(f"🚀 Iniciando processamento de {len(DATA_SOURCES)} anos...")

    # 5. Loop de Download e Validação
    for ano, file_id in DATA_SOURCES.items():
        # Trava de segurança para IDs não configurados
        if file_id.startswith("ID_AQUI"):
            print(f"⚠️  Pulando ano {ano}: ID não configurado.")
            continue

        print(f"\n--- Processando Ano: {ano} ---")
        
        # Monta a URL e o caminho do arquivo temporário
        drive_url = f"https://drive.google.com/uc?id={file_id}"
        zip_path = TEMP_DIR / f"download_{ano}.zip"
        
        try:
            # Baixa o arquivo silenciosamente
            gdown.download(drive_url, str(zip_path), quiet=True)

            # Extração do ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                csv_name = zip_ref.namelist()[0]
                zip_ref.extract(csv_name, path=TEMP_DIR)
                csv_path = TEMP_DIR / csv_name

            # Leitura e Validação com Pandas
            df = pd.read_csv(csv_path, sep=';', encoding='latin-1', low_memory=False)
            current_header = list(df.columns)

            if first_header is None:
                first_header = current_header
                all_dataframes.append(df)
                print(f"✅ {ano}: Arquivo base carregado ({len(df)} linhas).")
            else:
                if current_header == first_header:
                    all_dataframes.append(df)
                    print(f"✅ {ano}: Cabeçalho validado e dados acumulados ({len(df)} linhas).")
                else:
                    print(f"❌ {ano}: ERRO! Cabeçalho incompatível. Este ano será ignorado.")

        except Exception as e:
            print(f"❌ Erro ao processar {ano}: {e}")

    # 6. Consolidação Final (Indentação ajustada: fora do loop for)
    if all_dataframes:
        print("\n--- Consolidando arquivos ---")
        # Junta todos os DataFrames empilhando-os
        df_final = pd.concat(all_dataframes, ignore_index=True)
        
        # Salva o arquivo final com a data no nome
        df_final.to_csv(FINAL_FILE, sep=';', encoding='latin-1', index=False)
        
        print(f"✨ Sucesso! Arquivo consolidado salvo em: {FINAL_FILE}")
        print(f"📊 Total final de registros: {len(df_final):,}".replace(',', '.'))
        
        # Cálculo do tamanho do arquivo em MB
        tamanho_bytes = FINAL_FILE.stat().st_size
        tamanho_mb = tamanho_bytes / (1024 * 1024)
        print(f"💾 Tamanho final do arquivo: {tamanho_mb:.2f} MB")
        
    else:
        print("\n❌ Nenhum dado foi processado com sucesso.")

    # 7. Limpeza da pasta temporária
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)

if __name__ == "__main__":
    main()
