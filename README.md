# TFG Audit Logs - Sistema de Auditoria de Logs mediante Blockchain

Sistema que garantiza la **integridad e inmutabilidad** de los registros de auditoria (logs) utilizando Arboles de Merkle y Smart Contracts en Ethereum.

Si un atacante modifica o elimina logs del sistema, el verificador detecta la manipulacion al comparar los hashes recalculados con los almacenados inmutablemente en la blockchain.

## Arquitectura

El sistema sigue una arquitectura hibrida **Off-Chain / On-Chain**:

```
Logs (disco)  -->  Middleware (Merkle Tree)  -->  Smart Contract (Ethereum)
                                                         |
Dashboard (Flask)  <--  Verificador  <-------------------+
```

| Capa | Componente | Descripcion |
|------|-----------|-------------|
| Generacion | `creador_logs.py` | Simulador honeypot que genera trafico de ataques (SSH, SQL injection, etc.) |
| Middleware | `middleware.py` + `merkle.py` | Agrupa logs en lotes, construye el Arbol de Merkle y ancla la raiz en blockchain |
| Blockchain | `LogAuditor.sol` | Smart Contract que almacena las Merkle Roots de forma inmutable |
| Verificacion | `verificador.py` | Recalcula los hashes y los cruza con la blockchain para detectar manipulaciones |
| Presentacion | `app.py` + `index.html` | Dashboard web con logs en tiempo real y boton de auditoria |

## Stack Tecnologico

- **Blockchain:** Ethereum (Ganache v7.x, local)
- **Smart Contract:** Solidity 0.8.0
- **Backend:** Python 3.11, Web3.py, Flask
- **Criptografia:** SHA-256, Merkle Trees
- **Frontend:** HTML5, JavaScript, TailwindCSS

## Estructura del Proyecto

```
TFG_Audit_Logs/
├── src/
│   ├── contracts/
│   │   └── LogAuditor.sol          # Smart Contract
│   ├── middleware/
│   │   ├── merkle.py               # Implementacion del Arbol de Merkle
│   │   ├── middleware.py            # Agente de anclaje (watchdog + batching)
│   │   └── verificador.py          # Motor de verificacion de integridad
│   └── web/
│       ├── app.py                  # Servidor Flask (API + dashboard)
│       └── templates/
│           └── index.html          # Dashboard de auditoria
├── scripts/
│   ├── creador_logs.py             # Simulador de logs (honeypot)
│   └── deploy.py                   # Despliegue del Smart Contract
├── start.py                        # Pipeline de inicio unificado
├── requirements.txt                # Dependencias Python
└── .env                            # Variables de entorno (no incluido)
```

## Requisitos Previos

- Python 3.11+
- Node.js (para Ganache)
- Ganache CLI (`npm install -g ganache`)

## Instalacion

```bash
# Clonar el repositorio
git clone https://github.com/gcedugc/TFG_Audit_Logs.git
cd TFG_Audit_Logs

# Crear entorno virtual e instalar dependencias
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

# Configurar variables de entorno
# Crear un archivo .env en la raiz del proyecto con:
# GANACHE_URL=http://127.0.0.1:7545
# PRIVATE_KEY=tu_clave_privada_de_ganache
```

## Uso

### Inicio rapido (recomendado)

```bash
python start.py
```

Esto arranca automaticamente: Ganache, despliega el contrato, inicia el simulador de logs, el middleware de anclaje y el dashboard web.

Abrir el navegador en **http://localhost:5000**.

### Inicio manual

```bash
# 1. Iniciar Ganache en otra terminal
ganache --port 7545

# 2. Desplegar el Smart Contract
python scripts/deploy.py

# 3. Iniciar el simulador de logs
python scripts/creador_logs.py

# 4. Iniciar el middleware de anclaje
python src/middleware/middleware.py

# 5. Iniciar el dashboard web
python src/web/app.py
```

## Como Funciona

1. El **simulador** genera logs de ataques simulados (fuerza bruta SSH, inyeccion SQL, escaneos de puertos)
2. El **middleware** monitoriza el archivo de logs y agrupa cada 5 lineas en un lote
3. Para cada lote se construye un **Arbol de Merkle** y se extrae la raiz (32 bytes)
4. La raiz se envia al **Smart Contract** en una unica transaccion (ahorro de gas)
5. Al pulsar "Ejecutar Auditoria" en el dashboard, el **verificador** recalcula los hashes desde disco y los compara con la blockchain
6. Si algun log fue modificado o eliminado, el sistema lo detecta y muestra la evidencia original

## Coste de Gas

| Operacion | Gas |
|-----------|-----|
| Deploy del contrato | ~765,000 |
| `saveBatchRoot` (por lote) | ~210,000 |

El uso de Merkle Trees reduce el coste a **una transaccion por lote**, independientemente del numero de logs agrupados.
