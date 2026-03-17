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
├── benchmark_results.json              # Resultados del benchmark
├── requirements.txt                    # Dependencias Python
└── .env                                # Variables de entorno (no incluido en el repo)
```

## Requisitos Previos

- **Python 3.11+**
- **Node.js** (para Ganache)
- **Ganache CLI**: `npm install -g ganache`
- **MetaMask** (solo para Sepolia, opcional)
- **Cuenta en Alchemy** (solo para Sepolia, opcional)

## Instalacion

```bash
# 1. Clonar el repositorio
git clone https://github.com/gcedugc/TFG_Audit_Logs.git
cd TFG_Audit_Logs

# 2. Crear entorno virtual e instalar dependencias
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

# 3. Crear archivo .env en la raiz del proyecto (ver seccion Configuracion)
```

## Configuracion (.env)

Crear un archivo `.env` en la raiz del proyecto:

```env
# === Red local (Ganache) ===
GANACHE_URL=http://127.0.0.1:7545
GANACHE_PRIVATE_KEY=tu_clave_privada_de_ganache

# === Red publica (Sepolia) — Opcional ===
SEPOLIA_URL=https://eth-sepolia.g.alchemy.com/v2/TU_API_KEY
SEPOLIA_PRIVATE_KEY=tu_clave_privada_de_metamask
```

Para usar **Sepolia** se necesita:
1. Cuenta en [Alchemy](https://www.alchemy.com/) con app en red Sepolia
2. Wallet MetaMask con SepoliaETH (faucet: [sepoliafaucet.com](https://sepoliafaucet.com))
3. Exportar la clave privada de MetaMask (Configuracion > Seguridad > Mostrar clave privada)

## Uso

### Inicio rapido (recomendado)

```bash
python start.py
```

El pipeline presenta un **selector de red** y arranca automaticamente todos los servicios:

```
=======================================================
   TFG Audit Logs - Pipeline de Inicio
=======================================================

  Selecciona la red:
    1) Ganache (local)  — http://127.0.0.1:7545
    2) Sepolia (testnet) — https://eth-sepolia.g.alchemy.com/...

  Opcion [1/2]:
```

Servicios que levanta `start.py`:
1. Verificacion de prerequisitos (.env, Ganache/Sepolia, clave privada)
2. Limpieza de datos de sesiones anteriores
3. Conexion a la blockchain (Ganache local o Sepolia remota)
4. Despliegue del Smart Contract (`deploy.py`)
5. Simulador de logs honeypot (`creador_logs.py`)
6. Middleware de anclaje Merkle (`middleware.py`)
7. Dashboard web Flask (`app.py`)

Abrir el navegador en **http://localhost:5000**

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

### Flujo principal

1. El **simulador honeypot** genera logs de ataques simulados (fuerza bruta SSH, peticiones HTTP maliciosas, errores de BD, alertas de sistema)
2. El **middleware** monitoriza `sistema.log` y agrupa cada N lineas (BATCH_SIZE=5) en un lote, o cuando pasan 10 segundos (TIME_WINDOW)
3. Para cada lote se construye un **Arbol de Merkle** con SHA-256 y se extrae la raiz (32 bytes)
4. La raiz se envia al **Smart Contract** en una unica transaccion (ahorro de gas)
5. Las pruebas Merkle se guardan localmente en `merkle_proofs.json` (formato JSONL)

### Verificacion de integridad

Al pulsar **"Ejecutar Auditoria"** en el dashboard:

1. Se cargan los logs actuales de `sistema.log`
2. Se cargan las pruebas de `merkle_proofs.json`
3. Para cada lote se consulta la blockchain para verificar que la raiz existe
4. Se recalcula el Arbol de Merkle desde los logs del lote y se compara con la raiz almacenada
5. Se cruza cada log del lote contra el fichero actual — si falta alguno, se marca como **MANIPULADO**

### Estados del dashboard

El dashboard presenta tres estados posibles tras ejecutar la auditoria:

| Estado | Descripcion |
|--------|-------------|
| **Sistema Integro** (verde) | Todos los logs coinciden con la blockchain. Sin manipulaciones detectadas. |
| **Manipulacion detectada** (rojo) | Se abre un modal con el detalle de cada log manipulado o eliminado, mostrando el contenido original. |
| **No se pudo verificar** (ambar) | Error de conexion con el nodo blockchain o contrato no encontrado. |

### Deteccion de manipulacion

Si un atacante modifica o elimina un log:
- El hash recalculado **no coincidira** con la Merkle Root almacenada en blockchain
- El log faltante se detecta al cruzar con las pruebas locales
- El dashboard muestra un **modal de alerta** con la evidencia del log original

## Smart Contract (LogAuditor.sol)

```solidity
// Funciones principales
saveBatchRoot(bytes32 _merkleRoot, uint256 _logCount, string _range)  // Anclar lote
verifyBatch(bytes32 _merkleRoot) -> (bool, uint256, uint256, string)  // Verificar lote
getTotalBatches() -> uint256                                          // Total de lotes
```

- Solo el **owner** puede anclar lotes (modifier `onlyOwner`)
- Cada lote se almacena con: timestamp, auditor, numero de logs, rango temporal, numero de bloque
- Emite evento `BatchAnchored` para indexacion
- Proteccion contra duplicados: rechaza raices ya registradas

## Coste de Gas

| Operacion | Gas |
|-----------|-----|
| Deploy del contrato | ~765,000 |
| `saveBatchRoot` (por lote) | ~210,000 |

El uso de Merkle Trees reduce el coste a **una transaccion por lote**, independientemente del numero de logs agrupados.

## Benchmark

El script `scripts/benchmark.py` ejecuta pruebas automatizadas con diferentes valores de BATCH_SIZE:

```bash
python scripts/benchmark.py
```

Ejecuta 5 rondas con `BATCH_SIZE = [1, 5, 10, 25, 50]`, generando ~50 logs por ronda. Para cada ronda mide:
- Numero de lotes procesados
- Gas medio por transaccion de anclaje
- Tiempo medio de verificacion (promedio de 3 intentos)

Los resultados se muestran en tabla y se guardan en `benchmark_results.json`.

### Resultados obtenidos (Ganache local)

| BATCH_SIZE | Logs | Lotes | Gas por lote | Tiempo verificacion |
|------------|------|-------|-------------|---------------------|
| 1          |   52 |    52 |     211,170 |              468 ms |
| 5          |   51 |    10 |     219,778 |              115 ms |
| 10         |   51 |     8 |     226,129 |               97 ms |
| 25         |   51 |     8 |     231,240 |               99 ms |
| 50         |   52 |     8 |     235,372 |              104 ms |

**Conclusiones:**
- El gas por lote es practicamente constante (~210k-235k), independientemente del numero de logs agrupados
- BATCH_SIZE=1 genera muchas transacciones (una por log), aumentando el coste total y el tiempo de verificacion
- A partir de BATCH_SIZE=5, el tiempo de verificacion se reduce drasticamente (de 468ms a ~100ms)
- El balance optimo entre latencia y eficiencia se encuentra en BATCH_SIZE=5-10

## Redes Soportadas

| Red | Tipo | Uso | Modelo de Gas |
|-----|------|-----|---------------|
| Ganache | Local | Desarrollo y demos | Legacy (`gasPrice`) |
| Sepolia | Testnet publica | Validacion en red real | EIP-1559 (`maxFeePerGas`) |

La seleccion de red es transparente: `start.py` propaga `RPC_URL` y `PRIVATE_KEY` a todos los subprocesos. Cada modulo adapta los parametros de gas automaticamente segun la red detectada.

Al desplegar en Sepolia, el sistema muestra el enlace al contrato en Etherscan para verificar las transacciones publicamente.

## API REST

| Endpoint | Metodo | Descripcion |
|----------|--------|-------------|
| `/` | GET | Dashboard HTML |
| `/api/logs` | GET | Ultimas 50 lineas de `sistema.log` |
| `/api/audit` | GET | Ejecuta verificacion de integridad y devuelve JSON |

### Formato de respuesta `/api/audit`

```json
{
  "summary": {
    "total": 50,
    "valid": 48,
    "corrupt": 2,
    "batches_verified": 10
  },
  "details": [
    {
      "type": "TAMPERING",
      "original_content": "Mar 12 10:30:15 srv-finanzas-01 sshd[1234]: Failed password...",
      "batch_id": 3,
      "batch_status": "VALID"
    }
  ]
}
```

## Tipos de Logs Simulados

El honeypot genera cuatro tipos de logs:

| Tipo | Ejemplo |
|------|---------|
| **SSH** | `Mar 12 10:30:15 srv-finanzas-01 sshd[1234]: Failed password for root from 45.33.32.156 port 22 ssh2` |
| **HTTP** | `192.168.1.50 - - [12/Mar/2026:10:30:15] "GET /admin/login.php HTTP/1.1" 401 1234` |
| **Base de datos** | `2026-03-12 10:30:15 ERROR [InnoDB] Access denied for user` |
| **Sistema** | `Mar 12 10:30:15 srv-finanzas-01 kernel[456]: Disk utilization reached 90%` |
