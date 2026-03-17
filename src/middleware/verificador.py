import json
import sys
from web3 import Web3
import os
from datetime import datetime
from dotenv import load_dotenv

# Rutas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from src.middleware.merkle import MerkleTree

# Cargar variables de entorno
load_dotenv(os.path.join(BASE_DIR, ".env"))

LOG_FILE = os.path.join(BASE_DIR, "Logs", "sistema.log")
CONFIG_FILE = os.path.join(BASE_DIR, "contract_config.json")
PROOF_FILE = os.path.join(BASE_DIR, "Logs", "merkle_proofs.json")
# RPC_URL lo establece start.py; si no existe, usar GANACHE_URL como fallback
RPC_URL = os.getenv("RPC_URL") or os.getenv("GANACHE_URL")

# Colores para la terminal
class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def cargar_contrato(web3):
    if not os.path.exists(CONFIG_FILE):
        print(f"{Colors.FAIL}[!] ERROR: No se encuentra {CONFIG_FILE}. Ejecuta deploy.py primero.{Colors.ENDC}")
        return None

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    return web3.eth.contract(address=config["contract_address"], abi=config["abi"])

def cargar_proofs():
    """Lee merkle_proofs.json en formato JSONL (una línea JSON por lote)."""
    if not os.path.exists(PROOF_FILE):
        return []
    with open(PROOF_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        return []
    # Soportar formato antiguo (JSON array) y nuevo (JSONL)
    if content.startswith("["):
        return json.loads(content)
    return [json.loads(line) for line in content.splitlines() if line.strip()]

def verificar_integridad(return_data=False):
    if not return_data:
        print(f"{Colors.BOLD}--- INICIANDO VERIFICACIÓN (SISTEMA MERKLE) ---{Colors.ENDC}")

    results = {
        "summary": {"total": 0, "valid": 0, "corrupt": 0, "batches_verified": 0},
        "details": []
    }

    web3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not web3.is_connected():
        if not return_data: print(f"{Colors.FAIL}[!] No se puede conectar al nodo ({RPC_URL}){Colors.ENDC}")
        results["summary"]["error"] = "No se puede conectar al nodo blockchain"
        return results
    contrato = cargar_contrato(web3)
    if not contrato:
        results["summary"]["error"] = "No se encuentra el contrato desplegado"
        return results

    # Cargar pruebas locales (formato JSONL)
    proofs = cargar_proofs()
    if not proofs:
        if not return_data: print(f"{Colors.FAIL}[!] No hay archivo de pruebas Merkle.{Colors.ENDC}")
        return results

    # Cargar logs actuales como set para búsqueda O(1)
    if not os.path.exists(LOG_FILE): return results
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        logs_actuales = set(l.strip() for l in f if l.strip())

    results["summary"]["total"] = len(logs_actuales)

    if not return_data:
        print(f"[*] Total logs en disco: {len(logs_actuales)}")
        print(f"[*] Total lotes procesados: {len(proofs)}\n")

    logs_verified = 0
    logs_failed = 0

    for i, batch in enumerate(proofs):
        root = batch['root']
        logs_in_batch = batch['logs']

        # 1. Verificar si el LOTE está en Blockchain (convertir a bytes32)
        root_bytes = bytes.fromhex(root)
        exists, ts, count, meta = contrato.functions.verifyBatch(root_bytes).call()
        results["summary"]["batches_verified"] += 1

        batch_status = "UNKNOWN"
        if not exists:
            if not return_data: print(f"{Colors.WARNING}[LOTE {i}] ROOT NO ENCONTRADA EN CHAIN{Colors.ENDC}")
            logs_failed += len(logs_in_batch)
            batch_status = "MISSING_ON_CHAIN"
        else:
            # Recalcular root usando el módulo compartido
            recalc_root = MerkleTree(logs_in_batch).get_root()
            chain_date = datetime.fromtimestamp(ts).strftime('%H:%M:%S')

            if recalc_root == root:
                 if not return_data: print(f"[LOTE {i}] {Colors.OKGREEN}VALIDO EN CHAIN{Colors.ENDC} ({chain_date})")
                 batch_status = "VALID"
            else:
                 if not return_data: print(f"[LOTE {i}] {Colors.FAIL}CORRUPCION INTERNA{Colors.ENDC}")
                 batch_status = "CORRUPT"

        # 2. Cruzar con log actual en disco (O(1) por búsqueda en set)
        for log in logs_in_batch:
            if log in logs_actuales:
                logs_verified += 1
            else:
                logs_failed += 1

                error_detail = {
                    "type": "TAMPERING",
                    "original_content": log,
                    "batch_id": i,
                    "batch_status": batch_status
                }
                results["details"].append(error_detail)

                if not return_data:
                    print(f"    -> {Colors.FAIL}[ALERTA] LOG MANIPULADO/BORRADO{Colors.ENDC}")
                    print(f"       Original: {log}")

    results["summary"]["valid"] = logs_verified
    results["summary"]["corrupt"] = logs_failed

    if not return_data:
        print("\n" + "="*50)
        print(f"RESUMEN MERKLE AUDIT:")
        print(f"Logs validados: {logs_verified}")
        print(f"Logs corruptos: {logs_failed}")
        print("="*50)

    return results

if __name__ == "__main__":
    verificar_integridad()
