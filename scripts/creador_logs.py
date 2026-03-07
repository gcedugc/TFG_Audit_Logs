import time
import random
from datetime import datetime
import os

# Base Directory: scripts/ -> root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "Logs", "sistema.log")

ATTACKER_IPS = [
    "192.168.1.50",    
    "45.33.32.156",   
    "103.20.50.1",    
    "185.200.118.90", 
    "203.0.113.195"    
]

TARGET_USERS = [
    "root", "admin", "support", "user", "oracle", "postgres", "guest", "ubuntu"
]
PORTS = [22, 2222]

def get_timestamp():
    return datetime.now().strftime("%b %d %H:%M:%S")

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE"]
HTTP_PATHS = [
    "/admin/login.php", "/wp-admin/install.php", "/api/v1/users", 
    "/shell.php", "/db_backup.sql", "/etc/passwd", "/var/www/html/index.html"
]
STATUS_CODES = [200, 301, 401, 403, 404, 500, 503]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", 
    "Mozilla/5.0 (X11; Linux x86_64)", 
    "sqlmap/1.4.7#stable", 
    "Nikto/2.1.6"
]

DB_ERRORS = [
    "Connection refused", "Too many connections", "Deadlock found when trying to get lock",
    "Access denied for user", "Unknown database 'production'"
]

SYS_MESSAGES = [
    "Disk utilization reached 90%", "Out of memory: Kill process", 
    "USB device attached", "Failed to start service apache2"
]

def generate_ssh_log():
    """Genera logs de SSH (Honeypot)"""
    ip = random.choice(ATTACKER_IPS)
    user = random.choice(TARGET_USERS)
    port = random.choice(PORTS)
    pid = random.randint(1000, 9999)
    hostname = "srv-finanzas-01"
    
    event_types = [
        f"Failed password for {user} from {ip} port {port} ssh2",
        f"Invalid user {user} from {ip} port {port}",
        f"Connection closed by {ip} port {port} [preauth]",
        f"Received disconnect from {ip} port {port}:11: Bye Bye [preauth]"
    ]
    return f"{get_timestamp()} {hostname} sshd[{pid}]: {random.choice(event_types)}"

def generate_web_log():
    """Genera logs de servidor Web (Apache/Nginx style)"""
    ip = random.choice(ATTACKER_IPS)
    method = random.choice(HTTP_METHODS)
    path = random.choice(HTTP_PATHS)
    status = random.choice(STATUS_CODES)
    size = random.randint(100, 5000)
    ua = random.choice(USER_AGENTS)
    
    return f'{ip} - - [{datetime.now().strftime("%d/%b/%Y:%H:%M:%S %z")}] "{method} {path} HTTP/1.1" {status} {size} "-" "{ua}"'

def generate_db_log():
    """Genera logs de base de datos"""
    level = random.choice(["WARNING", "ERROR", "CRITICAL"])
    msg = random.choice(DB_ERRORS)
    return f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {level} [InnoDB] {msg}"

def generate_sys_log():
    """Genera logs de sistema"""
    hostname = "srv-finanzas-01"
    proc = random.choice(["kernel", "systemd", "cron"])
    pid = random.randint(100, 999)
    msg = random.choice(SYS_MESSAGES)
    return f"{get_timestamp()} {hostname} {proc}[{pid}]: {msg}"

def generate_random_log():
    """Elige aleatoriamente un tipo de log para generar"""
    generators = [generate_ssh_log, generate_web_log, generate_db_log, generate_sys_log]
    return random.choice(generators)()

def main():

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    print(f"[*] Iniciando Honeypot Simulator (Multiservicio)...")
    print(f"[*] Escribiendo logs variados en: {LOG_FILE}")
    print("----------------------------------------------------")

    try:
        while True:

            linea = generate_random_log()
            
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(linea + "\n")
            
            print(f"[+] Log generado: {linea}")
            
            time.sleep(random.uniform(0.5, 3))
            
    except KeyboardInterrupt:
        print("\n[!] Deteniendo el simulador de Honeypot.")

if __name__ == "__main__":
    main()
