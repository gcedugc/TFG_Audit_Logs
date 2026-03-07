import time
import json
import sys
from web3 import Web3
import os

from dotenv import load_dotenv

# Determinar la ruta base del proyecto (2 niveles arriba: src/middleware -> src -> root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from src.middleware.merkle import MerkleTree

# Cargar variables de entorno
load_dotenv(os.path.join(BASE_DIR, ".env"))

LOG_FILE = os.path.join(BASE_DIR, "Logs", "sistema.log")
CONFIG_FILE = os.path.join(BASE_DIR, "contract_config.json")
PROOF_FILE = os.path.join(BASE_DIR, "Logs", "merkle_proofs.json")

GANACHE_URL = os.getenv("GANACHE_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

def cargar_contrato(web3):
    if not os.path.exists(CONFIG_FILE):
        print(f"[!] ERROR: No se encuentra {CONFIG_FILE}. Ejecuta deploy.py primero.")
        return None

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    return web3.eth.contract(address=config["contract_address"], abi=config["abi"])

def anclar_lote(web3, contrato, merkle_root, log_count, batch_range, account_address):
    try:
        print(f"[*] Anclando Lote Merkle (Root: {merkle_root[:10]}... | Logs: {log_count}) -> ", end="")

        # Convertir hash hex string a bytes32 para el contrato
        root_bytes = bytes.fromhex(merkle_root)

        tx = contrato.functions.saveBatchRoot(root_bytes, log_count, batch_range).build_transaction({
            'from': account_address,
            'nonce': web3.eth.get_transaction_count(account_address),
            'gasPrice': web3.eth.gas_price
        })

        signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

        print(f"¡OK! (Bloque {receipt.blockNumber})")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def guardar_prueba_local(batch_data):
    """Escribe el lote como una línea JSON al final del archivo (append incremental)."""
    with open(PROOF_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(batch_data) + "\n")

def main():
    print("--- INICIANDO SISTEMA DE AUDITORÍA (MERKLE BATCHING) ---")

    web3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    if not web3.is_connected():
        print("[!] No se puede conectar a Ganache.")
        return

    account = web3.eth.account.from_key(PRIVATE_KEY)
    contrato = cargar_contrato(web3)
    if not contrato: return

    print(f"[*] Auditor: {account.address}")
    print(f"[*] Modo: Agrupación por Merkle Trees (Ahorro de gas y privacidad)")

    BATCH_SIZE = 5
    TIME_WINDOW = 10

    buffer_logs = []
    last_flush = time.time()

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            f.seek(0, 0)

            while True:
                current_pos = f.tell()
                linea = f.readline()

                should_flush = False

                if linea:
                    linea = linea.strip()
                    if linea:
                        buffer_logs.append(linea)
                else:
                    time.sleep(1)
                    f.seek(current_pos)

                # Condiciones para enviar lote
                time_elapsed = time.time() - last_flush
                if len(buffer_logs) >= BATCH_SIZE or (len(buffer_logs) > 0 and time_elapsed > TIME_WINDOW):
                    should_flush = True

                if should_flush:
                    mt = MerkleTree(buffer_logs)
                    root = mt.get_root()
                    count = len(buffer_logs)
                    rango = f"Logs del {time.ctime()}"

                    success = anclar_lote(web3, contrato, root, count, rango, account.address)

                    if success:
                        batch_meta = {
                            "root": root,
                            "timestamp": time.time(),
                            "logs": buffer_logs.copy(),
                            "count": count
                        }
                        guardar_prueba_local(batch_meta)

                        buffer_logs = []
                        last_flush = time.time()

    except FileNotFoundError:
        print("[!] Archivo de logs no encontrado.")
    except KeyboardInterrupt:
        print("\n[!] Deteniendo.")

if __name__ == "__main__":
    main()
