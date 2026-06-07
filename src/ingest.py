import os
import shutil
import zipfile
import gdown
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

def contar_linhas_arquivo(caminho_arquivo: Path) -> int:
    """Conta de forma eficiente a quantidade de registros sem carregar o arquivo na RAM."""
    linhas = 0
    with open(caminho_arquivo, 'r', encoding='latin-1') as f:
        for _ in f:
            linhas += 1
    # Subtrai 1 para remover o cabeçalho da contagem de registros reais
    return max(0, linhas - 1)

def main():
    # 1. Carrega as variáveis de ambiente do arquivo .env
    load_dotenv()

    # 2. Configurações de Pastas e Data
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    RAW_DIR = PROJECT_ROOT / "data" / "raw"
    TEMP_DIR = RAW_DIR / "temp_extraction" 
    
    # Gerando a data da ingestão para o arquivo principal bruto ajustado para o padrão mestre
    datestamp = datetime.now().strftime("%Y-%m-%d")
    FINAL_RAW_FILE = RAW_DIR / f"prf_191_{datestamp}.csv"

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Check de Idempotência (Garante append-only e evita retrabalho)
    if FINAL_RAW_FILE.exists():
        print(f"⚠️  Atenção: O arquivo bruto para o dia {datestamp} já existe na RAW.")
        print("⏭️  Pulando a ingestão para garantir a imutabilidade do diretório.")
        return

    # Só cria a pasta temporária se o processo for realmente rodar
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # 4. Mapeamento de Anos usando EXCLUSIVAMENTE os IDs do Dataset Geral/Complexo
    DATA_SOURCES = {
        "2025": "1-PJGRbfSe7PVjU37A3wTCls_NRXyVGRD",
        "2024": "14qBOhrE1gioVtuXgxkCJ9kCA8YtUGXKA",  
        "2023": "1-caam_dahYOf2eorq4mez04Om6DD5d_3", 
        "2022": "1wskEgRC3ame7rncSDQ7qWhKsoKw1lohY",
        "2021": "1Gk3U6cMOZIevsDZHLi6J503xoCRS_lnI",
    }

    print(f"🚀 Iniciando download do dataset geral de {len(DATA_SOURCES)} anos...")

    # Lista para controlar os arquivos CSV descompactados temporariamente
    temp_csv_files = []
    relatorio_linhas_por_ano = {}

    # 5. Loop de Ingestão de Dados Brutos
    for ano, id_drive in DATA_SOURCES.items():
        print(f"\n--- 📅 Processando Ano: {ano} ---")
        zip_path = TEMP_DIR / f"geral_{ano}.zip"
        
        try:
            print(f"📥 Baixando arquivo comprimido do ano {ano}...")
            gdown.download(f"https://drive.google.com/uc?id={id_drive}", str(zip_path), quiet=True)

            print(f"📦 Extraindo conteúdo bruto...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                csv_original_name = zip_ref.namelist()[0]
                # Criamos um nome padronizado temporário para evitar conflitos de encoding no file system
                csv_temp_path = TEMP_DIR / f"raw_{ano}.csv"
                
                zip_ref.extract(csv_original_name, path=TEMP_DIR)
                (TEMP_DIR / csv_original_name).rename(csv_temp_path)
                
                temp_csv_files.append(csv_temp_path)
                print(f"✅ Ano {ano} extraído com sucesso.")

                # Realiza a contagem volumétrica do ano corrente de forma otimizada
                qtd_linhas = contar_linhas_arquivo(csv_temp_path)
                relatorio_linhas_por_ano[ano] = qtd_linhas
                print(f"📊 Volumetria Identificada para {ano}: {qtd_linhas:,} registros.")

        except Exception as e:
            print(f"❌ Erro crítico ao baixar/extrair o ano {ano}: {e}")

    # 6. Empilhamento e Consolidação dos CSVs Brutos (Mantendo formato original)
    if temp_csv_files:
        print("\n--- 📦 Consolidando Arquivo Final na Camada RAW ---")
        try:
            first_file = True
            with open(FINAL_RAW_FILE, 'w', encoding='latin-1') as outfile:
                for temp_csv in temp_csv_files:
                    with open(temp_csv, 'r', encoding='latin-1') as infile:
                        # Lê a primeira linha (cabeçalho)
                        header = infile.readline()
                        
                        # Se for o primeiro arquivo da lista, escreve o cabeçalho
                        if first_file:
                            outfile.write(header)
                            first_file = False
                        
                        # Escreve o restante das linhas do corpo do arquivo
                        shutil.copyfileobj(infile, outfile)
                    print(f"➕ Agregado com sucesso: {temp_csv.name}")

            # Contagem final e emissão dos indicadores para a governança
            total_geral_registros = contar_linhas_arquivo(FINAL_RAW_FILE)

            print("\n==========================================================")
            print("📊 RELATÓRIO DE VOLUMETRIA POR SÉRIE HISTÓRICA (RAW)")
            print("==========================================================")
            for ano_ref, total_ano in sorted(relatorio_linhas_por_ano.items()):
                print(f" ──> Ano {ano_ref}: {total_ano:,} linhas de indivíduos.")
            print("──────────────────────────────────────────────────────────")
            print(f" Total Geral Consolidado: {total_geral_registros:,} registros empilhados.")
            print("==========================================================")

            print(f"\n✨ Sucesso! Base geral imutável salva em: {FINAL_RAW_FILE}")
            print(f"💾 Tamanho total do CSV bruto: {FINAL_RAW_FILE.stat().st_size / (1024*1024):.2f} MB")

        except Exception as e:
            print(f"❌ Erro ao consolidar os arquivos CSV: {e}")

    # 7. Limpeza e expurgo da pasta temporária
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    print("\n🧹 Pasta temporária limpa com sucesso. Ingestão Concluída!")

if __name__ == "__main__":
    main()