# TFG Audit Logs - Sistema de Auditoria de Logs mediante Blockchain

Sistema que garantiza la **integridad e inmutabilidad** de los registros de auditoria (logs) utilizando Arboles de Merkle y Smart Contracts en Ethereum.

Si un atacante modifica o elimina logs del sistema, el verificador detecta la manipulacion al comparar los hashes recalculados con los almacenados inmutablemente en la blockchain.

## Arquitectura

El sistema sigue una arquitectura hibrida **Off-Chain / On-Chain**:

```
                        ┌──────────────────────────────┐
                        │   Ethereum (Ganache/Sepolia)  │
                        │   Smart Contract LogAuditor   │
                        │   (Merkle Roots inmutables)   │
                        └──────────┬───────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │  ANCLAR            │  VERIFICAR          │
              ▼                    ▼                     │
┌──────────────────┐    ┌──────────────────┐    ┌───────┴──────────┐
│  Middleware       │    │  Verificador     │    │  Dashboard Flask  │
│  (Merkle Batch)  │    │  (Integridad)    │    │  (localhost:5000) │
└────────┬─────────┘    └──────────────────┘    └──────────────────┘
         │
         ▼
┌──────────────────┐
│  sistema.log     │ ◄── Honeypot Simulator (creador_logs.py)
│  (logs en disco) │
└──────────────────┘
```

| Capa | Componente | Descripcion |
|------|-----------|-------------|
| Generacion | `creador_logs.py` | Simulador honeypot que genera trafico de ataques (SSH, HTTP, BD, sistema) |
| Middleware | `middleware.py` + `merkle.py` | Agrupa logs en lotes, construye el Arbol de Merkle y ancla la raiz en blockchain |
| Blockchain | `LogAuditor.sol` | Smart Contract que almacena las Merkle Roots de forma inmutable |
| Verificacion | `verificador.py` | Recalcula los hashes y los cruza con la blockchain para detectar manipulaciones |
| Presentacion | `app.py` + `index.html` | Dashboard web con logs en tiempo real y boton de auditoria |

## Stack Tecnologico

| Tecnologia | Version | Proposito |
|-----------|---------|-----------|
| Python | 3.11 | Backend, middleware, scripts |
| Solidity | 0.8.0 | Smart Contract |
| Web3.py | 7.14.0 | Interaccion con Ethereum |
| Flask | 3.1.2 | Servidor web y API REST |
| Ganache | 7.x | Blockchain local de desarrollo |
| Sepolia | Testnet | Red publica de pruebas Ethereum |
| TailwindCSS | CDN | Estilos del dashboard |
| SHA-256 | - | Funcion hash criptografica |

## Estructura del Proyecto

```
TFG_Audit_Logs/
├── src/
│   ├── contracts/
│   │   └── LogAuditor.sol              # Smart Contract (Solidity 0.8.0)
│   ├── middleware/
│   │   ├── merkle.py                   # Implementacion del Arbol de Merkle (SHA-256)
│   │   ├── middleware.py               # Agente de anclaje (watchdog + batching)
│   │   └── verificador.py             # Motor de verificacion de integridad
│   └── web/
│       ├── app.py                      # Servidor Flask (API + dashboard)
│       └── templates/
│           └── index.html              # Dashboard de auditoria (TailwindCSS)
├── scripts/
│   ├── creador_logs.py                 # Simulador de logs (honeypot multiservicio)
│   ├── deploy.py                       # Despliegue del Smart Contract
│   └── benchmark.py                    # Benchmark automatizado con BATCH_SIZE variable
├── Logs/                               # Directorio de datos (generado en ejecucion)
│   ├── sistema.log                     # Logs del honeypot
│   └── merkle_proofs.json              # Pruebas Merkle en formato JSONL
├── start.py                            # Pipeline de inicio unificado (selector de red)
├── contract_config.json                # Direccion y ABI del contrato desplegado
├── requirements.txt                    # Dependencias Python
└── .env                                # Variables de entorno (no incluido en el repo)
```

## Requisitos Previos

- **Python 3.11+**
- **Node.js** (para Ganache)
- **Ganache CLI**: `npm install -g ganache`
- **MetaMask** y cuenta en **Alchemy** (solo para Sepolia)

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
```

## Configuracion (.env)

Crear un archivo `.env` en la raiz del proyecto:

```env
# Red local (Ganache)
GANACHE_URL=http://127.0.0.1:7545
GANACHE_PRIVATE_KEY=tu_clave_privada_de_ganache

# Red publica (Sepolia) — Opcional
SEPOLIA_URL=https://eth-sepolia.g.alchemy.com/v2/TU_API_KEY
SEPOLIA_PRIVATE_KEY=tu_clave_privada_de_metamask
```

## Uso

```bash
python start.py
```

El sistema presenta un selector de red y arranca todos los servicios automaticamente:

```
  Selecciona la red:
    1) Ganache (local)
    2) Sepolia (testnet)
```

Abrir el navegador en **http://localhost:5000**

## Como Funciona

1. El **simulador honeypot** genera logs de ataques simulados (SSH, HTTP, BD, sistema)
2. El **middleware** agrupa los logs en lotes y construye un **Arbol de Merkle** con SHA-256
3. La raiz del arbol se ancla en el **Smart Contract** en una unica transaccion
4. Al pulsar **"Ejecutar Auditoria"** en el dashboard, el **verificador** recalcula los hashes y los compara con la blockchain
5. Si algun log fue modificado o eliminado, el sistema lo detecta y muestra la evidencia original

## Coste de Gas

| Operacion | Gas |
|-----------|-----|
| Deploy del contrato | ~765,000 |
| `saveBatchRoot` (por lote) | ~210,000 |

El uso de Merkle Trees reduce el coste a **una transaccion por lote**, independientemente del numero de logs agrupados.
