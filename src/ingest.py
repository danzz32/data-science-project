import os
import shutil
from pathlib import Path
import kagglehub
from dotenv import load_dotenv

def main():
    # 1. Carrega as variáveis de ambiente do arquivo .env
    load_dotenv()

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    RAW_DIR = PROJECT_ROOT / "data" / "raw"
    RAW_FILE_PATH = RAW_DIR / "911.csv"

    # Garante que a pasta raw exista
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("⏳ Iniciando o processo de ingestão da API do Kaggle...")

    try:
        # 3. Baixa o dataset via kagglehub
        # O kagglehub autentica automaticamente se KAGGLE_USERNAME e KAGGLE_KEY estiverem no ambiente
        dataset_handle = "ahmadrafiee/911-calls-for-service-metadata-1-million-record"
        download_path = kagglehub.dataset_download(dataset_handle)
        
        # 4. Localiza o arquivo CSV baixado no cache do sistema
        files = [f for f in os.listdir(download_path) if f.endswith('.csv')]
        if not files:
            raise FileNotFoundError("Nenhum arquivo CSV foi encontrado no pacote baixado.")
        
        temp_csv_path = Path(download_path) / files[0]

        # 5. Move o arquivo para a nossa zona de aterrissagem (data/raw/)
        shutil.copy(temp_csv_path, RAW_FILE_PATH)
        print(f"✅ Ingestão concluída com sucesso!")
        print(f"📂 Dado bruto salvo de forma imutável em: {RAW_FILE_PATH}")

    except Exception as e:
        print(f"❌ Erro crítico durante a ingestão: {e}")

if __name__ == "__main__":
    main()