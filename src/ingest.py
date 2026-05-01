import os
import shutil
from pathlib import Path
from datetime import datetime #importação acrescentada
import kagglehub
from dotenv import load_dotenv

def main():
    # 1. Carrega as variáveis de ambiente do arquivo .env
    load_dotenv()

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    RAW_DIR = PROJECT_ROOT / "data" / "raw"
    datestamp = datetime.now().strftime("%Y-%m-%d") #variável para coleta de data
    RAW_FILE_PATH = RAW_DIR / f"911_{datestamp}.csv" #novo PATH já com informação de data
    #RAW_FILE_PATH = RAW_DIR / "911.csv" (código substituído)

    # Garante que a pasta raw exista
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # --- ALTERAÇÃO: CHECK DE IDEMPOTÊNCIA ---
    if RAW_FILE_PATH.exists():
        print(f"⚠️  Atenção: O arquivo '{RAW_FILE_PATH.name}' já existe na pasta de destino.")
        print("⏭️  Pulando a ingestão para evitar duplicidade e consumo desnecessário de API.")
        return # Finaliza a execução da função main() aqui
    # ----------------------------------------

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
        print("📊 Calculando o volume de dados ingeridos...") #print para informar início da contagem de registros
        # Abrindo o arquivo em modo leitura e contando linha por linha
        with open(RAW_FILE_PATH, 'r', encoding='utf-8') as f:
            # Conta todas as linhas e subtrai 1 (que é a linha do cabeçalho)
            total_registros = sum(1 for linha in f) - 1

            # Garante que o valor não seja negativo caso o arquivo esteja totalmente vazio
            total_registros = max(0, total_registros)

        # Formata o número com pontos para facilitar a leitura (ex: 1.000.000)
        numero_formatado = f"{total_registros:,}".replace(',', '.')
        print(f"📈 Total de registros coletados: {numero_formatado} linhas.")
        print(f"📂 Dado bruto salvo de forma imutável em: {RAW_FILE_PATH}")

    except Exception as e:
        print(f"❌ Erro crítico durante a ingestão: {e}")

if __name__ == "__main__":
    main()
