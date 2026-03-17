"""
Pipeline de inicio unificado - TFG Audit Logs
Ejecuta: python start.py
"""

import subprocess
import sys
import os
import time
import signal
import shutil
import atexit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Usar el Python del venv si existe
VENV_PYTHON = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = os.path.join(BASE_DIR, "venv", "bin", "python")
PYTHON = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

# Colores para Windows
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    BLUE   = "\033[94m"
    MAGENTA= "\033[95m"

# Habilitar colores ANSI en Windows
if os.name == 'nt':
    os.system('')

processes = []

def log(color, tag, msg):
    print(f"{color}{C.BOLD}[{tag}]{C.RESET} {msg}")

def cleanup():
    log(C.YELLOW, "STOP", "Deteniendo todos los servicios...")
    for name, proc in processes:
        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                log(C.YELLOW, "STOP", f"{name} detenido")
            except Exception:
                proc.kill()
                log(C.RED, "STOP", f"{name} forzado a cerrar")
    log(C.GREEN, "DONE", "Todos los servicios detenidos.")

atexit.register(cleanup)

def read_env(key, default=None):
    """Lee una variable del .env sin dependencias externas."""
    env_path = os.path.join(BASE_DIR, ".env")
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return default

def select_network():
    """Pregunta al usuario qué red utilizar."""
    ganache_url = read_env("GANACHE_URL")
    sepolia_url = read_env("SEPOLIA_URL")

    has_ganache = ganache_url is not None
    has_sepolia = sepolia_url is not None

    if has_ganache and has_sepolia:
        print(f"  {C.BOLD}Selecciona la red:{C.RESET}")
        print(f"    {C.GREEN}1){C.RESET} Ganache (local)  — {ganache_url}")
        print(f"    {C.CYAN}2){C.RESET} Sepolia (testnet) — {sepolia_url[:50]}...")
        print()
        choice = input(f"  Opción [1/2]: ").strip()
        if choice == "2":
            return "sepolia", sepolia_url
        return "ganache", ganache_url
    elif has_sepolia:
        return "sepolia", sepolia_url
    elif has_ganache:
        return "ganache", ganache_url
    else:
        log(C.RED, "ERROR", "No se encontró GANACHE_URL ni SEPOLIA_URL en .env")
        sys.exit(1)

def check_prerequisites(network):
    log(C.CYAN, "CHECK", "Verificando prerequisitos...")

    # .env
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        log(C.RED, "ERROR", f"No se encuentra .env en {BASE_DIR}")
        sys.exit(1)
    log(C.GREEN, "  OK ", ".env encontrado")

    # Ganache solo es necesario en modo local
    ganache_cmd = None
    if network == "ganache":
        ganache_cmd = shutil.which("ganache") or shutil.which("ganache-cli")
        if not ganache_cmd:
            log(C.RED, "ERROR", "Ganache no encontrado en PATH")
            log(C.YELLOW, "INFO", "Instálalo con: npm install -g ganache")
            sys.exit(1)
        log(C.GREEN, "  OK ", f"Ganache encontrado: {ganache_cmd}")
    else:
        log(C.GREEN, "  OK ", "Modo Sepolia (no requiere Ganache local)")

    # Private key (según la red seleccionada)
    if network == "ganache":
        pk = read_env("GANACHE_PRIVATE_KEY") or read_env("PRIVATE_KEY")
        key_name = "GANACHE_PRIVATE_KEY"
    else:
        pk = read_env("SEPOLIA_PRIVATE_KEY")
        key_name = "SEPOLIA_PRIVATE_KEY"
    if not pk:
        log(C.RED, "ERROR", f"{key_name} no encontrada en .env")
        sys.exit(1)
    log(C.GREEN, "  OK ", f"{key_name} configurada")

    return ganache_cmd

def start_ganache(ganache_cmd, ganache_url, private_key):
    from urllib.parse import urlparse
    port = str(urlparse(ganache_url).port or 8545)

    cmd = [ganache_cmd, "--port", port, "--quiet"]
    if private_key:
        cmd.extend(["--wallet.accounts", f"0x{private_key.lstrip('0x')},1000000000000000000000"])

    log(C.BLUE, "GANACHE", f"Iniciando blockchain local en puerto {port}...")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    processes.append(("Ganache", proc))

    import urllib.request
    import json as _json
    for i in range(15):
        try:
            req = urllib.request.Request(
                ganache_url,
                data=_json.dumps({"jsonrpc":"2.0","method":"net_version","params":[],"id":1}).encode(),
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=2)
            if resp.status == 200:
                log(C.GREEN, "GANACHE", f"Blockchain lista en {ganache_url}")
                return True
        except Exception:
            pass
        time.sleep(1)

    log(C.RED, "ERROR", "Ganache no respondió tras 15 segundos")
    sys.exit(1)

def check_sepolia_connection(rpc_url):
    """Verifica la conexión con Sepolia y muestra el balance."""
    import urllib.request
    import json as _json

    try:
        req = urllib.request.Request(
            rpc_url,
            data=_json.dumps({"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = _json.loads(resp.read().decode())
        chain_id = int(data["result"], 16)
        log(C.GREEN, "SEPOLIA", f"Conectado a Sepolia (Chain ID: {chain_id})")
        return True
    except Exception as e:
        log(C.RED, "ERROR", f"No se puede conectar a Sepolia: {e}")
        sys.exit(1)

def run_deploy():
    log(C.MAGENTA, "DEPLOY", "Desplegando Smart Contract...")
    result = subprocess.run(
        [PYTHON, os.path.join(BASE_DIR, "scripts", "deploy.py")],
        cwd=BASE_DIR,
    )
    if result.returncode != 0:
        log(C.RED, "ERROR", "Fallo al desplegar el contrato")
        sys.exit(1)
    log(C.GREEN, "DEPLOY", "Smart Contract desplegado correctamente")

def start_background(name, script_path, color):
    log(color, name, f"Iniciando {script_path}...")
    proc = subprocess.Popen(
        [PYTHON, os.path.join(BASE_DIR, script_path)],
        cwd=BASE_DIR,
    )
    processes.append((name, proc))
    return proc

def main():
    print()
    print(f"{C.BOLD}{C.CYAN}{'='*55}")
    print(f"   TFG Audit Logs - Pipeline de Inicio")
    print(f"{'='*55}{C.RESET}")
    print()

    # 1. Seleccionar red
    network, rpc_url = select_network()
    print()

    # Propagar la URL y private key elegidas a los subprocesos
    os.environ["RPC_URL"] = rpc_url
    if network == "ganache":
        os.environ["PRIVATE_KEY"] = read_env("GANACHE_PRIVATE_KEY") or read_env("PRIVATE_KEY")
    else:
        os.environ["PRIVATE_KEY"] = read_env("SEPOLIA_PRIVATE_KEY")

    # 2. Prerequisitos
    ganache_cmd = check_prerequisites(network)
    print()

    # 3. Limpiar datos de sesiones anteriores
    for f in ["Logs/sistema.log", "Logs/merkle_proofs.json"]:
        path = os.path.join(BASE_DIR, f)
        if os.path.exists(path):
            os.remove(path)
    os.makedirs(os.path.join(BASE_DIR, "Logs"), exist_ok=True)
    log(C.CYAN, "CLEAN", "Datos de sesiones anteriores limpiados")
    print()

    # 4. Conectar a la blockchain
    if network == "ganache":
        private_key = read_env("PRIVATE_KEY")
        start_ganache(ganache_cmd, rpc_url, private_key)
    else:
        check_sepolia_connection(rpc_url)
    print()

    # 5. Deploy
    run_deploy()
    print()

    # 6. Creador de logs (honeypot)
    start_background("HONEYPOT", os.path.join("scripts", "creador_logs.py"), C.YELLOW)
    time.sleep(2)

    # 7. Middleware (ancla en blockchain)
    start_background("MIDDLEWARE", os.path.join("src", "middleware", "middleware.py"), C.MAGENTA)
    time.sleep(1)
    print()

    # 8. Flask Web
    network_label = "Ganache local" if network == "ganache" else "Sepolia testnet"
    log(C.GREEN, "WEB", "Iniciando dashboard en http://localhost:5000")
    print()
    print(f"{C.BOLD}{C.GREEN}{'='*55}")
    print(f"   Todo listo! Abre http://localhost:5000")
    print(f"   Red: {network_label}")
    print(f"   Pulsa Ctrl+C para detener todo")
    print(f"{'='*55}{C.RESET}")
    print()

    flask_proc = subprocess.Popen(
        [PYTHON, os.path.join(BASE_DIR, "src", "web", "app.py")],
        cwd=BASE_DIR,
    )
    processes.append(("Flask", flask_proc))

    try:
        flask_proc.wait()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
