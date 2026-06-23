import os
<<<<<<< HEAD
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
=======
import time
import glob
import zipfile
import shutil
import requests
import urllib3
from pathlib import Path
from datetime import datetime
from requests.adapters import HTTPAdapter

# Desabilita avisos de certificados TLS/SSL inválidos gerados pelo site do governo
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MAX_RETRIES = 3
BACKOFF_FACTOR = 2
TIMEOUT_HTTP = 30

class FirefoxTLSAdapter(HTTPAdapter):
    """Adaptador de rede robusto que injeta cifras modernas para contornar restrições severas de SSL."""
    def init_poolmanager(self, *args, **kwargs):
        context = urllib3.util.ssl_.create_urllib3_context()
        context.set_ciphers('DEFAULT:@SECLEVEL=1:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256')
        context.check_hostname = False
        kwargs['ssl_context'] = context
        return super(FirefoxTLSAdapter, self).init_poolmanager(*args, **kwargs)

def contar_linhas_arquivo(caminho_arquivo: Path) -> int:
    """Conta de forma eficiente a quantidade de registros sem carregar o arquivo na RAM."""
    linhas = 0
    with open(caminho_arquivo, 'r', encoding='latin-1') as f:
        for _ in f:
            linhas += 1
    return max(0, linhas - 1)

def download_com_politica_retry(url: str, destino: Path) -> None:
    """Efetua o download contornando bloqueios de TLS com tratamento exponencial de erro."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3"
    }
    
    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            with requests.Session() as session:
                session.mount("https://", FirefoxTLSAdapter())
                session.mount("http://", FirefoxTLSAdapter())
                
                with session.get(url, headers=headers, stream=True, timeout=TIMEOUT_HTTP, verify=False) as r:
                    r.raise_for_status()
                    with open(destino, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=32768):
                            if chunk:
                                f.write(chunk)
            return
        except Exception as e:
            tempo_espera = BACKOFF_FACTOR ** tentativa
            print(f"  ⚠️ [Tentativa {tentativa}/{MAX_RETRIES}] Falha na comunicação TLS/HTTP: {e}")
            if tentativa == MAX_RETRIES:
                raise ConnectionError("Servidor indisponível ou rejeitando tráfego Python.")
            print(f"  🔄 Recuando estrategicamente por {tempo_espera}s...")
            time.sleep(tempo_espera)

def main():
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    RAW_DIR = PROJECT_ROOT / "data" / "raw"
    TEMP_DIR = RAW_DIR / "temp_extraction"
    
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # ─── VALIDAÇÃO DE IDEMPOTÊNCIA REAL HISTÓRICA ───
    # Busca por qualquer arquivo consolidado preexistente no diretório RAW
    arquivos_existentes = glob.glob(str(RAW_DIR / "prf_191_*.csv"))
    
    if arquivos_existentes:
        arquivo_original = Path(arquivos_existentes[0])
        print(f"⚠️  Idempotência Ativada: Base histórica original localizada em '{arquivo_original.name}'.")
        print("⏭️  Pulando a ingestão para evitar downloads redundantes e desperdício de armazenamento, além de manter a imutabilidade!")
        return

    # Se a pasta estiver vazia, realiza o primeiro download guardando o carimbo de hoje
    datestamp_hoje = datetime.now().strftime("%Y-%m-%d")
    FINAL_RAW_FILE = RAW_DIR / f"prf_191_{datestamp_hoje}.csv"

    FONTES_OFICIAIS = {
        "2025": "https://arquivos.prf.gov.br/arquivos/index.php/s/w7N1Z69O2gKfehZ/download",
        "2024": "https://arquivos.prf.gov.br/arquivos/index.php/s/77lY9mshU0D1z4v/download",
        "2023": "https://arquivos.prf.gov.br/arquivos/index.php/s/76vdf88UhY7z2pZ/download",
        "2022": "https://arquivos.prf.gov.br/arquivos/index.php/s/6v8y9YVNhU7Z1pW/download",
        "2021": "https://arquivos.prf.gov.br/arquivos/index.php/s/5V7y8YVNhU6Z1pW/download"
    }

    FONTES_CONTINGENCIA = {
        "2025": "https://docs.google.com/uc?export=download&id=1-PJGRbfSe7PVjU37A3wTCls_NRXyVGRD",
        "2024": "https://docs.google.com/uc?export=download&id=14qBOhrE1gioVtuXgxkCJ9kCA8YtUGXKA",
        "2023": "https://docs.google.com/uc?export=download&id=1-caam_dahYOf2eorq4mez04Om6DD5d_3",
        "2022": "https://docs.google.com/uc?export=download&id=1wskEgRC3ame7rncSDQ7qWhKsoKw1lohY",
        "2021": "https://docs.google.com/uc?export=download&id=1Gk3U6cMOZIevsDZHLi6J503xoCRS_lnI"
    }

    print(f"🚀 Base RAW vazia. Iniciando primeiro download do dataset de {len(FONTES_OFICIAIS)} anos...")
    temp_csv_files = []
    relatorio_linhas_por_ano = {}

    for ano in sorted(FONTES_OFICIAIS.keys()):
        print(f"\n--- 📅 Processando Ano: {ano} ---")
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = TEMP_DIR / f"download_{ano}.zip"
        csv_temp_path = TEMP_DIR / f"raw_{ano}.csv"
        
        url_alvo = FONTES_OFICIAIS[ano]
        print(f"📥 Conectando à Rota Primária (Portal de Dados Abertos PRF)...")
        try:
            download_com_politica_retry(url_alvo, zip_path)
        except (ConnectionError, Exception):
            print(f"⚠️  Alerta de instabilidade no site do Governo para o ano {ano}.")
            print(f"🔀 Chaveando dinamicamente para a rota de Failover...")
            url_alvo = FONTES_CONTINGENCIA[ano]
            try:
                download_com_politica_retry(url_alvo, zip_path)
            except Exception as e_failover:
                print(f"❌ Falha em ambas as rotas para o ano {ano}: {e_failover}")
                continue

        try:
            print(f"📦 Extraindo conteúdo bruto...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                csv_original = next((arq for arq in zip_ref.namelist() if arq.lower().endswith('.csv')), None)
                if not csv_original:
                    raise FileNotFoundError("Nenhum CSV encontrado dentro do zip.")
                
                zip_ref.extract(csv_original, path=TEMP_DIR)
                shutil.move(str(TEMP_DIR / csv_original), str(csv_temp_path))
                
            temp_csv_files.append(csv_temp_path)
            qtd_linhas = contar_linhas_arquivo(csv_temp_path)
            relatorio_linhas_por_ano[ano] = qtd_linhas
            print(f"✅ Ano {ano} extraído com sucesso ({qtd_linhas:,} registros).")
            
        except Exception as e:
            print(f"❌ Erro no processamento local do ano {ano}: {e}")

    if temp_csv_files:
        print("\n--- 📦 Consolidando Dataset Único na Camada RAW ---")
        try:
            first_file = True
            with open(FINAL_RAW_FILE, 'w', encoding='latin-1') as outfile:
                for temp_csv in temp_csv_files:
                    with open(temp_csv, 'r', encoding='latin-1') as infile:
                        header = infile.readline()
                        if first_file:
                            outfile.write(header)
                            first_file = False
                        shutil.copyfileobj(infile, outfile)
                    print(f"➕ Agregado: {temp_csv.name}")

            total_geral = contar_linhas_arquivo(FINAL_RAW_FILE)

            print("\n==========================================================")
            print(f"📊 RELATÓRIO DE VOLUMETRIA CONSOLIDADA - BRUTO ({datestamp_hoje})")
            print("==========================================================")
            for ano_ref, total_ano in sorted(relatorio_linhas_por_ano.items()):
                print(f" ──> Série Histórica {ano_ref}: {total_ano:,} linhas.")
            print("──────────────────────────────────────────────────────────")
            print(f" Total Geral Unificado: {total_geral:,} registros empilhados.")
            print("==========================================================")
            print(f"\n✨ Sucesso! Base original salva em: {FINAL_RAW_FILE}")
            print(f"💾 Tamanho do arquivo final: {FINAL_RAW_FILE.stat().st_size / (1024*1024):.2f} MB")

        except Exception as e:
            print(f"❌ Erro na consolidação do arquivo final: {e}")

    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    print("\n🧹 Pasta temporária limpa. Ingestão Concluída!")

if __name__ == "__main__":
    main()
>>>>>>> 0dd1dc22f33a32648db475cb4785a79ef073fed3
