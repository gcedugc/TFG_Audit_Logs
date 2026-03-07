from flask import Flask, render_template, jsonify
import sys
import os
import threading
import time

# Permitir importar módulos de src/middleware
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.middleware import verificador

app = Flask(__name__)

# Configuraciones básicas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_FILE = os.path.join(BASE_DIR, "Logs", "sistema.log")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/logs')
def get_logs():
    """Devuelve las últimas 50 líneas del log"""
    if not os.path.exists(LOG_FILE):
        return jsonify({"logs": ["Esperando logs..."]})
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    return jsonify({"logs": [l.strip() for l in lines[-50:]]})

@app.route('/api/audit')
def audit():
    """Ejecuta el verificador y devuelve resultados"""
    results = verificador.verificar_integridad(return_data=True)
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
