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

def check_prerequisites():
    log(C.CYAN, "CHECK", "Verificando prerequisitos...")

    # .env
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        log(C.RED, "ERROR", f"No se encuentra .env en {BASE_DIR}")
        log(C.YELLOW, "INFO", "Crea un archivo .env con GANACHE_URL y PRIVATE_KEY")
        sys.exit(1)
    log(C.GREEN, "  OK ", ".env encontrado")

    # Ganache
    ganache_cmd = shutil.which("ganache") or shutil.which("ganache-cli")
    if not ganache_cmd:
        log(C.RED, "ERROR", "Ganache no encontrado en PATH")
        log(C.YELLOW, "INFO", "Instálalo con: npm install -g ganache")
        sys.exit(1)
    log(C.GREEN, "  OK ", f"Ganache encontrado: {ganache_cmd}")

    return ganache_cmd

def read_ganache_url():
    """Lee GANACHE_URL del .env sin dependencias externas."""
    ganache_url = "http://127.0.0.1:8545"
    env_path = os.path.join(BASE_DIR, ".env")
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("GANACHE_URL="):
                ganache_url = line.split("=", 1)[1].strip().strip('"').strip("'")
    return ganache_url

def read_private_key():
    """Lee PRIVATE_KEY del .env sin dependencias externas."""
    env_path = os.path.join(BASE_DIR, ".env")
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("PRIVATE_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None

def start_ganache(ganache_cmd):
    ganache_url = read_ganache_url()
    private_key = read_private_key()

    # Extraer el puerto de la URL para arrancar Ganache en el puerto correcto
    from urllib.parse import urlparse
    parsed = urlparse(ganache_url)
    port = str(parsed.port or 8545)

    # Arrancar Ganache con la clave privada del .env como cuenta fondeada
    cmd = [ganache_cmd, "--port", port, "--quiet"]
    if private_key:
        cmd.extend(["--wallet.accounts", f"0x{private_key.lstrip('0x')},1000000000000000000000"])

    log(C.BLUE, "GANACHE", f"Iniciando blockchain local en puerto {port}...")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
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

    # 1. Prerequisitos
    ganache_cmd = check_prerequisites()
    print()

    # 2. Limpiar datos de sesiones anteriores
    for f in ["Logs/sistema.log", "Logs/merkle_proofs.json"]:
        path = os.path.join(BASE_DIR, f)
        if os.path.exists(path):
            os.remove(path)
    os.makedirs(os.path.join(BASE_DIR, "Logs"), exist_ok=True)
    log(C.CYAN, "CLEAN", "Datos de sesiones anteriores limpiados")
    print()

    # 3. Ganache
    start_ganache(ganache_cmd)
    print()

    # 4. Deploy
    run_deploy()
    print()

    # 4. Creador de logs (honeypot)
    start_background("HONEYPOT", os.path.join("scripts", "creador_logs.py"), C.YELLOW)
    time.sleep(2)

    # 5. Middleware (ancla en blockchain)
    start_background("MIDDLEWARE", os.path.join("src", "middleware", "middleware.py"), C.MAGENTA)
    time.sleep(1)
    print()

    # 6. Flask Web
    log(C.GREEN, "WEB", "Iniciando dashboard en http://localhost:5000")
    print()
    print(f"{C.BOLD}{C.GREEN}{'='*55}")
    print(f"   Todo listo! Abre http://localhost:5000")
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
