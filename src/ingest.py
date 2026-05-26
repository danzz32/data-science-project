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
    
    # Gerando a data da ingestão para o arquivo principal
    datestamp = datetime.now().strftime("%Y-%m-%d")
    FINAL_FILE = RAW_DIR / f"prf_191_{datestamp}.csv"
    LOOKUP_FILE = RAW_DIR / "lookup_testemunhas.parquet"

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Check de Idempotência (Validador de existência)
    if FINAL_FILE.exists() and LOOKUP_FILE.exists():
        print(f"⚠️  Atenção: Os arquivos de ingestão para o dia {datestamp} já existem.")
        print("⏭️  Pulando a ingestão para evitar duplicidade e retrabalho.")
        return

    # Só cria a pasta temporária se o processo for realmente rodar
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # 4. Mapeamento de Anos e IDs Duplos (Acidentes e Pessoas)
    # Insira aqui os IDs corretos do Google Drive para cada categoria
    DATA_SOURCES = {
        "2025": {"acidentes": "1-G3MdmHBt6CprDwcW99xxC4BZ2DU5ryR", "pessoas": "1-PJGRbfSe7PVjU37A3wTCls_NRXyVGRD"},
        "2024": {"acidentes": "14lB0vqMFkaZj8HZ44b0njYgxs9nAN8KO", "pessoas": "14qBOhrE1gioVtuXgxkCJ9kCA8YtUGXKA"},  
        "2023": {"acidentes": "1-WO3SfNrwwZ5_l7fRTiwBKRw7mi1-HUq", "pessoas": "1-caam_dahYOf2eorq4mez04Om6DD5d_3"}, 
        "2022": {"acidentes": "1PRQjuV5gOn_nn6UNvaJyVURDIfbSAK4-", "pessoas": "1wskEgRC3ame7rncSDQ7qWhKsoKw1lohY"},
        "2021": {"acidentes": "12xH8LX9aN2gObR766YN3cMcuycwyCJDz", "pessoas": "1Gk3U6cMOZIevsDZHLi6J503xoCRS_lnI"},
    }

    all_dataframes_acidentes = []
    all_dataframes_testemunhas = []
    first_header = None

    print(f"🚀 Iniciando processamento duplo (Acidentes + Pessoas) de {len(DATA_SOURCES)} anos...")

    # 5. Loop de Download, Validação e Extração de Testemunhas
    for ano, ids in DATA_SOURCES.items():
        id_acidentes = ids["acidentes"]
        id_pessoas = ids["pessoas"]

        if id_acidentes.startswith("ID_AQUI") or id_pessoas.startswith("ID_AQUI"):
            print(f"⚠️  Pulando ano {ano}: IDs não configurados completamente.")
            continue

        print(f"\n--- 📅 Processando Ano: {ano} ---")
        
        # Paths temporários para os ZIPs
        zip_acidentes = TEMP_DIR / f"acidentes_{ano}.zip"
        zip_pessoas = TEMP_DIR / f"pessoas_{ano}.zip"
        
        try:
            # -----------------------------------------------------------------
            # PARTE A: PROCESSAR DATASET PRINCIPAL (ACIDENTES)
            # -----------------------------------------------------------------
            print(f"📥 Baixando base de acidentes {ano}...")
            gdown.download(f"https://drive.google.com/uc?id={id_acidentes}", str(zip_acidentes), quiet=True)

            with zipfile.ZipFile(zip_acidentes, 'r') as zip_ref:
                csv_name = zip_ref.namelist()[0]
                zip_ref.extract(csv_name, path=TEMP_DIR)
                csv_path = TEMP_DIR / csv_name

            df_acidentes = pd.read_csv(csv_path, sep=';', encoding='latin-1', low_memory=False)
            current_header = list(df_acidentes.columns)

            # Validação de Estrutura (Garante que os CSVs de acidentes empilham perfeitamente)
            if first_header is None:
                first_header = current_header
                all_dataframes_acidentes.append(df_acidentes)
                print(f"✅ Acidentes {ano}: Base definida como padrão ({len(df_acidentes)} linhas).")
            else:
                if current_header == first_header:
                    all_dataframes_acidentes.append(df_acidentes)
                    print(f"✅ Acidentes {ano}: Cabeçalho validado ({len(df_acidentes)} linhas).")
                else:
                    print(f"❌ Acidentes {ano}: ERRO! Cabeçalho incompatível. Ignorando este ano.")
                    continue  # Pula o processamento de pessoas se a base de acidentes falhar

            # Deleta o CSV de acidentes extraído para liberar espaço antes de baixar o próximo
            if csv_path.exists():
                csv_path.unlink()

            # -----------------------------------------------------------------
            # PARTE B: PROCESSAR DATASET SECUNDÁRIO (PESSOAS) -> Abordagem de Lookup
            # -----------------------------------------------------------------
            print(f"📥 Baixando base de pessoas {ano}...")
            gdown.download(f"https://drive.google.com/uc?id={id_pessoas}", str(zip_pessoas), quiet=True)

            with zipfile.ZipFile(zip_pessoas, 'r') as zip_ref:
                csv_name_pessoas = zip_ref.namelist()[0]
                zip_ref.extract(csv_name_pessoas, path=TEMP_DIR)
                csv_path_pessoas = TEMP_DIR / csv_name_pessoas

            # STREAMING SELETIVO: Lê apenas o ID e o Tipo de Envolvido para poupar muita memória RAM
            df_pessoas = pd.read_csv(
                csv_path_pessoas, 
                sep=';', 
                encoding='latin-1', 
                usecols=['id', 'tipo_envolvido'], 
                low_memory=False
            )

            # Padroniza strings para contagem exata
            df_pessoas['tipo_envolvido'] = df_pessoas['tipo_envolvido'].astype(str).str.lower().str.strip()
            
            # Filtra apenas testemunhas e agrupa contando as ocorrências por ID
            df_testemunhas = df_pessoas[df_pessoas['tipo_envolvido'] == 'testemunha']
            df_contagem = df_testemunhas.groupby('id').size().reset_index(name='total_testemunhas')
            
            all_dataframes_testemunhas.append(df_contagem)
            print(f"✅ Pessoas {ano}: Isoladas testemunhas de {len(df_contagem)} acidentes diferentes.")

            # Deleta o CSV de pessoas extraído
            if csv_path_pessoas.exists():
                csv_path_pessoas.unlink()

        except Exception as e:
            print(f"❌ Erro crítico ao processar o ano {ano}: {e}")

    # 6. Consolidação dos Dois Destinos Finais (Fora do Loop)
    
    # Destino 1: O arquivo consolidado de Acidentes
    if all_dataframes_acidentes:
        print("\n--- 📦 Consolidando Base de Acidentes ---")
        df_final_acidentes = pd.concat(all_dataframes_acidentes, ignore_index=True)
        df_final_acidentes.to_csv(FINAL_FILE, sep=';', encoding='latin-1', index=False)
        print(f"✨ Sucesso! Base de acidentes salva em: {FINAL_FILE}")
        print(f"📊 Total de registros agregados: {len(df_final_acidentes):,}".replace(',', '.'))
        print(f"💾 Tamanho do CSV: {FINAL_FILE.stat().st_size / (1024*1024):.2f} MB")
        
    # Destino 2: O arquivo consolidado de Lookup (Testemunhas dos 5 anos juntos)
    if all_dataframes_testemunhas:
        print("\n--- ⚙️ Consolidando Lookup Table de Testemunhas ---")
        df_final_lookup = pd.concat(all_dataframes_testemunhas, ignore_index=True)
        
        # Garante soma caso um ID se repita em arquivos cruzados
        df_final_lookup = df_final_lookup.groupby('id')['total_testemunhas'].sum().reset_index()
        
        # Salva em PARQUET: Levíssimo, rápido e tipado
        df_final_lookup.to_parquet(LOOKUP_FILE, index=False)
        print(f"✅ Lookup Table gerada com sucesso em: {LOOKUP_FILE}")
        print(f"📊 IDs mapeados com testemunhas: {len(df_final_lookup):,}".replace(',', '.'))
        print(f"💾 Tamanho do Parquet: {LOOKUP_FILE.stat().st_size / 1024:.2f} KB")

    # 7. Limpeza e expurgo final da pasta temporária
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    print("\n🧹 Pasta temporária limpa com sucesso. Ingestão Concluída!")

if __name__ == "__main__":
    main()
