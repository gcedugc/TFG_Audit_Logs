"""
Benchmark automatizado - Pruebas con BATCH_SIZE variable
Ejecuta 5 rondas con BATCH_SIZE = [1, 5, 10, 25, 50], recoge métricas
y genera una tabla de resultados.

Uso: python scripts/benchmark.py
"""

import subprocess
import sys
import os
import time
import re
import json
import shutil
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Usar el Python del venv
VENV_PYTHON = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = os.path.join(BASE_DIR, "venv", "bin", "python")
PYTHON = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

MIDDLEWARE_PATH = os.path.join(BASE_DIR, "src", "middleware", "middleware.py")
LOG_FILE = os.path.join(BASE_DIR, "Logs", "sistema.log")
PROOF_FILE = os.path.join(BASE_DIR, "Logs", "merkle_proofs.json")
CONFIG_FILE = os.path.join(BASE_DIR, "contract_config.json")

TARGET_LOGS = 50
BATCH_SIZES = [1, 5, 10, 25, 50]

# Colores ANSI
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    CYAN    = "\033[96m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"

if os.name == 'nt':
    os.system('')


def log(color, tag, msg):
    print(f"{color}{C.BOLD}[{tag}]{C.RESET} {msg}")


def read_env(key, default=None):
    env_path = os.path.join(BASE_DIR, ".env")
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return default


def set_batch_size(size):
    """Modifica BATCH_SIZE en middleware.py."""
    with open(MIDDLEWARE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r'BATCH_SIZE\s*=\s*\d+', f'BATCH_SIZE = {size}', content)
    with open(MIDDLEWARE_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def clean_data():
    """Elimina logs y proofs de sesiones anteriores."""
    for path in [LOG_FILE, PROOF_FILE]:
        if os.path.exists(path):
            os.remove(path)
    os.makedirs(os.path.join(BASE_DIR, "Logs"), exist_ok=True)


def count_logs():
    if not os.path.exists(LOG_FILE):
        return 0
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def count_proofs():
    if not os.path.exists(PROOF_FILE):
        return 0
    with open(PROOF_FILE, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def wait_for_ganache(url, timeout=20):
    for _ in range(timeout):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps({"jsonrpc": "2.0", "method": "net_version", "params": [], "id": 1}).encode(),
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=2)
            if resp.status == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def wait_for_flask(url="http://127.0.0.1:5000/api/logs", timeout=15):
    for _ in range(timeout):
        try:
            resp = urllib.request.urlopen(url, timeout=2)
            if resp.status == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def wait_for_logs_and_batches(batch_size, timeout=180):
    """Espera a que haya >= TARGET_LOGS y que el middleware haya procesado todos los lotes."""
    start = time.time()
    while time.time() - start < timeout:
        n_logs = count_logs()
        n_proofs = count_proofs()
        # Necesitamos suficientes logs Y que se hayan procesado en lotes
        expected_batches = n_logs // batch_size
        if n_logs >= TARGET_LOGS and n_proofs >= expected_batches and n_proofs > 0:
            # Esperar un poco más para que el último lote termine
            time.sleep(3)
            return True
        time.sleep(2)
    return False


def measure_audit(n_tries=3):
    """Llama a /api/audit y mide el tiempo de respuesta (promedio de n intentos)."""
    times = []
    result = None
    for _ in range(n_tries):
        t0 = time.perf_counter()
        try:
            resp = urllib.request.urlopen("http://127.0.0.1:5000/api/audit", timeout=30)
            data = json.loads(resp.read().decode())
            elapsed = (time.perf_counter() - t0) * 1000  # ms
            times.append(elapsed)
            result = data
        except Exception as e:
            log(C.RED, "ERROR", f"Fallo al llamar /api/audit: {e}")
        time.sleep(0.5)
    avg_time = sum(times) / len(times) if times else 0
    return avg_time, result


def get_gas_data(ganache_url):
    """Obtiene gas del deploy y gas por saveBatchRoot ejecutando un subproceso con el venv."""
    script = f"""
import json
from web3 import Web3
web3 = Web3(Web3.HTTPProvider("{ganache_url}"))
if not web3.is_connected():
    print(json.dumps({{"error": "no connection"}}))
else:
    block_num = web3.eth.block_number
    deploy_gas = 0
    batch_gas_list = []
    for i in range(block_num):
        block = web3.eth.get_block(i + 1, full_transactions=True)
        for tx in block.transactions:
            receipt = web3.eth.get_transaction_receipt(tx.hash)
            if i == 0:
                deploy_gas = receipt.gasUsed
            else:
                batch_gas_list.append(receipt.gasUsed)
    avg_gas = sum(batch_gas_list) / len(batch_gas_list) if batch_gas_list else 0
    print(json.dumps({{"deploy_gas": deploy_gas, "avg_gas": avg_gas, "total_txs": len(batch_gas_list)}}))
"""
    result = subprocess.run([PYTHON, "-c", script], capture_output=True, text=True, cwd=BASE_DIR)
    if result.returncode != 0:
        log(C.RED, "ERROR", f"Gas script falló: {result.stderr.strip()}")
        return 0, 0, 0
    try:
        data = json.loads(result.stdout.strip())
        if "error" in data:
            return 0, 0, 0
        return data["deploy_gas"], data["avg_gas"], data["total_txs"]
    except Exception:
        return 0, 0, 0


def kill_processes(procs):
    for name, proc in procs:
        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()


def run_single_benchmark(batch_size, ganache_cmd, ganache_url, private_key):
    """Ejecuta una ronda completa de benchmark para un BATCH_SIZE dado."""
    procs = []

    try:
        # 1. Configurar BATCH_SIZE
        set_batch_size(batch_size)
        log(C.CYAN, "CONFIG", f"BATCH_SIZE = {batch_size}")

        # 2. Limpiar datos
        clean_data()

        # 3. Arrancar Ganache
        from urllib.parse import urlparse
        port = str(urlparse(ganache_url).port or 8545)
        ganache_args = [ganache_cmd, "--port", port, "--quiet"]
        if private_key:
            ganache_args.extend(["--wallet.accounts", f"0x{private_key.lstrip('0x')},1000000000000000000000"])
        proc = subprocess.Popen(ganache_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append(("Ganache", proc))

        if not wait_for_ganache(ganache_url):
            log(C.RED, "ERROR", "Ganache no respondió")
            return None
        log(C.GREEN, "GANACHE", "Lista")

        # 4. Deploy
        result = subprocess.run([PYTHON, os.path.join(BASE_DIR, "scripts", "deploy.py")],
                                cwd=BASE_DIR, capture_output=True, text=True)
        if result.returncode != 0:
            log(C.RED, "ERROR", f"Deploy falló: {result.stderr}")
            return None
        log(C.GREEN, "DEPLOY", "OK")

        # 5. Honeypot
        proc = subprocess.Popen([PYTHON, os.path.join(BASE_DIR, "scripts", "creador_logs.py")],
                                cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append(("Honeypot", proc))
        time.sleep(2)

        # 6. Middleware
        proc = subprocess.Popen([PYTHON, os.path.join(BASE_DIR, "src", "middleware", "middleware.py")],
                                cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append(("Middleware", proc))
        time.sleep(1)

        # 7. Flask
        proc = subprocess.Popen([PYTHON, os.path.join(BASE_DIR, "src", "web", "app.py")],
                                cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append(("Flask", proc))

        if not wait_for_flask():
            log(C.RED, "ERROR", "Flask no respondió")
            return None
        log(C.GREEN, "FLASK", "Lista")

        # 8. Esperar a que se generen logs y se procesen los lotes
        log(C.YELLOW, "WAIT", f"Esperando ~{TARGET_LOGS} logs y procesamiento de lotes...")
        if not wait_for_logs_and_batches(batch_size):
            log(C.RED, "WARN", "Timeout esperando logs/lotes")

        n_logs = count_logs()
        n_batches = count_proofs()
        log(C.CYAN, "STATS", f"Logs: {n_logs} | Lotes procesados: {n_batches}")

        # 9. Medir auditoría
        log(C.MAGENTA, "AUDIT", "Midiendo tiempo de verificación (promedio de 3 intentos)...")
        audit_time, audit_result = measure_audit(n_tries=3)
        log(C.GREEN, "AUDIT", f"Tiempo medio: {audit_time:.0f} ms")

        # 10. Obtener datos de gas
        deploy_gas, avg_batch_gas, total_txs = get_gas_data(ganache_url)
        log(C.BLUE, "GAS", f"Deploy: {deploy_gas:,} | Avg batch: {avg_batch_gas:,.0f} | Txs: {total_txs}")

        return {
            "batch_size": batch_size,
            "logs": n_logs,
            "batches": n_batches,
            "avg_gas": round(avg_batch_gas),
            "total_txs": total_txs,
            "audit_time_ms": round(audit_time),
            "valid": audit_result["summary"]["valid"] if audit_result else 0,
            "corrupt": audit_result["summary"]["corrupt"] if audit_result else 0,
        }

    finally:
        kill_processes(procs)
        time.sleep(2)  # Dar tiempo a que los puertos se liberen


def print_results_table(results):
    """Imprime la tabla de resultados formateada."""
    print()
    print(f"{C.BOLD}{C.CYAN}{'='*85}")
    print(f"   RESULTADOS DEL BENCHMARK")
    print(f"{'='*85}{C.RESET}")
    print()

    header = f"{'BATCH_SIZE':>10} | {'Logs':>6} | {'Lotes':>6} | {'Gas/lote':>10} | {'Transacciones':>13} | {'T. Verificación':>15}"
    separator = "-" * len(header)

    print(f"{C.BOLD}{header}{C.RESET}")
    print(separator)

    for r in results:
        print(f"{r['batch_size']:>10} | {r['logs']:>6} | {r['batches']:>6} | {r['avg_gas']:>10,} | {r['total_txs']:>13} | {r['audit_time_ms']:>12} ms")

    print(separator)
    print()

    # Tabla en formato Markdown para copiar
    print(f"{C.BOLD}Tabla Markdown (copiar para la memoria):{C.RESET}")
    print()
    print("| BATCH_SIZE | Logs | Lotes | Gas por lote | Transacciones | Tiempo verificación |")
    print("|------------|------|-------|-------------|---------------|---------------------|")
    for r in results:
        print(f"| {r['batch_size']:>10} | {r['logs']:>4} | {r['batches']:>5} | {r['avg_gas']:>11,} | {r['total_txs']:>13} | {r['audit_time_ms']:>15} ms |")
    print()


def main():
    print()
    print(f"{C.BOLD}{C.CYAN}{'='*55}")
    print(f"   TFG Audit Logs - Benchmark Automatizado")
    print(f"   BATCH_SIZES: {BATCH_SIZES}")
    print(f"   TARGET_LOGS: ~{TARGET_LOGS} por ronda")
    print(f"{'='*55}{C.RESET}")
    print()

    # Verificar prerequisitos
    ganache_cmd = shutil.which("ganache") or shutil.which("ganache-cli")
    if not ganache_cmd:
        log(C.RED, "ERROR", "Ganache no encontrado en PATH")
        sys.exit(1)

    ganache_url = read_env("GANACHE_URL", "http://127.0.0.1:7545")
    private_key = read_env("PRIVATE_KEY")

    results = []
    original_batch_size = 5  # Valor original para restaurar al final

    for i, bs in enumerate(BATCH_SIZES):
        print()
        print(f"{C.BOLD}{C.MAGENTA}{'─'*55}")
        print(f"   RONDA {i+1}/{len(BATCH_SIZES)} — BATCH_SIZE = {bs}")
        print(f"{'─'*55}{C.RESET}")
        print()

        result = run_single_benchmark(bs, ganache_cmd, ganache_url, private_key)
        if result:
            results.append(result)
            log(C.GREEN, "DONE", f"Ronda BATCH_SIZE={bs} completada")
        else:
            log(C.RED, "FAIL", f"Ronda BATCH_SIZE={bs} falló")

    # Restaurar BATCH_SIZE original
    set_batch_size(original_batch_size)
    log(C.CYAN, "RESTORE", f"BATCH_SIZE restaurado a {original_batch_size}")

    # Resultados
    if results:
        print_results_table(results)

        # Guardar resultados en JSON
        output_path = os.path.join(BASE_DIR, "benchmark_results.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        log(C.GREEN, "SAVE", f"Resultados guardados en {output_path}")
    else:
        log(C.RED, "ERROR", "No se completó ninguna ronda")


if __name__ == "__main__":
    main()
