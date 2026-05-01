import os
import shutil
import zipfile
import gdown
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

def main():
    # 1. Carrega as variáveis de ambiente do arquivo .env
    load_dotenv()

    # 2. Configuração de caminhos
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    RAW_DIR = PROJECT_ROOT / "data" / "raw"
    
    # Geramos o sufixo de data
    datestamp = datetime.now().strftime("%Y-%m-%d")
    RAW_FILE_PATH = RAW_DIR / f"prf_191_{datestamp}.csv"

    # Garante que a pasta raw exista
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Check de Idempotência
    if RAW_FILE_PATH.exists():
        print(f"⚠️  Atenção: O arquivo '{RAW_FILE_PATH.name}' já existe.")
        print("⏭️  Pulando a ingestão para evitar duplicidade e retrabalho.")
        return 

    # 4. Configuração do link de download (Drive ID extraído da URL)
    FILE_ID = "1-PJGRbfSe7PVjU37A3wTCls_NRXyVGRD"
    DRIVE_URL = f"https://drive.google.com/uc?id={FILE_ID}"
    
    temp_download_path = RAW_DIR / "temp_download.zip"

    print(f"⏳ Iniciando o download dos Dados Abertos da PRF via Google Drive...")

    try:
        # 5. Download do arquivo burlando a tela de aviso do Drive
        gdown.download(DRIVE_URL, str(temp_download_path), quiet=False)

        if not temp_download_path.exists():
            raise FileNotFoundError("Falha no download. O arquivo não foi salvo no disco.")

        print("📦 Download finalizado. Processando arquivo...")

        # 6. Verifica se é um arquivo ZIP e extrai o CSV
        if zipfile.is_zipfile(temp_download_path):
            print("🗜️  Arquivo ZIP detectado. Extraindo...")
            with zipfile.ZipFile(temp_download_path, 'r') as zip_ref:
                # Pega o nome do primeiro arquivo dentro do ZIP (o CSV da PRF)
                csv_filename = zip_ref.namelist()[0]
                extracted_path = zip_ref.extract(csv_filename, path=RAW_DIR)
                
                # Move e renomeia para o padrão do nosso projeto
                shutil.move(extracted_path, RAW_FILE_PATH)
        else:
            # Caso no futuro o governo mude e entregue o CSV direto, o código não quebra
            shutil.move(temp_download_path, RAW_FILE_PATH)

        # Limpa o arquivo .zip temporário
        if temp_download_path.exists():
            temp_download_path.unlink()

        print(f"✅ Ingestão concluída com sucesso! Arquivo salvo em: {RAW_FILE_PATH}")

        # 7. Contagem de Registros
        print("📊 Calculando o volume de dados ingeridos...")
        
        # Lendo com latin-1 por padrão dos arquivos do governo brasileiro
        with open(RAW_FILE_PATH, 'r', encoding='latin-1', errors='ignore') as f:
            total_registros = sum(1 for linha in f) - 1 # O '-1' desconta o cabeçalho
            total_registros = max(0, total_registros)
        
        numero_formatado = f"{total_registros:,}".replace(',', '.')
        print(f"📈 Total de registros coletados: {numero_formatado} linhas.")

    except Exception as e:
        print(f"❌ Erro crítico durante a ingestão: {e}")

if __name__ == "__main__":
    main()
