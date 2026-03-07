# Capítulo 4: Arquitectura y Diseño del Sistema

## 4.1. Visión General de la Arquitectura

El sistema propuesto implementa una arquitectura **descentralizada e híbrida (Off-Chain / On-Chain)**, diseñada para garantizar la integridad, inmutabilidad y disponibilidad de los registros de auditoría del sistema operativo. 

El diseño se estructura en cuatro capas lógicas claramente diferenciadas que interactúan de forma modular:

1.  **Capa de Generación de Datos (Data Layer):** Origen de los eventos (logs del sistema).
2.  **Capa de Middleware (Logic Layer):** Procesamiento criptográfico y comunicación con la Blockchain.
3.  **Capa de Persistencia Distribuida (Blockchain Layer):** Almacenamiento inmutable de las huellas digitales.
4.  **Capa de Presentación (User Interface Layer):** Visualización y verificación forense para el administrador.

Esta separación de responsabilidades permite que el sistema sea escalable y que la carga computacional pesada (hashing) se realice fuera de la cadena (*Off-Chain*), utilizando la Blockchain únicamente como un notario digital eficiente (*On-Chain*).

## 4.2. Stack Tecnológico

La selección de tecnologías se ha basado en criterios de robustez, adopción industrial y compatibilidad con entornos Linux/Unix:

| Componente | Tecnología | Versión | Justificación |
| :--- | :--- | :--- | :--- |
| **Blockchain** | Ethereum (Ganache) | v7.x | Estandar de facto para Smart Contracts. Ganache permite simulación local de bajo coste. |
| **Lenguaje Contrato** | Solidity | v0.8.0 | Lenguaje tipado y seguro para la EVM (Ethereum Virtual Machine). |
| **Middleware** | Python | v3.11 | Versatilidad para manejo de archivos I/O y potentes librerías criptográficas. |
| **Librería Web3** | Web3.py | v6.x | Interfaz estándar para conectar Python con nodos Ethereum RPC. |
| **Backend Web** | Flask | v3.x | Framework ligero para exponer la API de verificación. |
| **Frontend** | HTML5 + TailwindCSS | - | Diseño moderno y responsivo para el Dashboard de control. |
| **Hashing** | SHA-256 | - | Algoritmo de hash criptográfico estándar resistente a colisiones. |

## 4.3. Diseño Detallado de Componentes

### 4.3.1. Capa de Generación (Honeypot Simulator)
Esta capa es la responsable de simular un entorno hostil. Se ha desarrollado un script (`creador_logs.py`) que inyecta eventos sintéticos en el archivo `/var/log/syslog` (o equivalente local `Logs/sistema.log`).
*   **Funcionalidad:** Genera patrones de tráfico normal y ataques simulados (Fuerza bruta SSH, Inyección SQL, Errores de Kernel).
*   **Propósito:** Proveer un flujo de datos continuo para testear la capacidad de respuesta del Middleware.

### 4.3.2. Middleware de Anclaje (Middleware.py)
Es el núcleo lógico del sistema. Actúa como un *Daemon* o servicio en segundo plano con las siguientes responsabilidades:
*   **Monitorización (Watchdog):** Escucha cambios en el archivo de logs en tiempo real.
*   **Merkle Tree Batching:** En lugar de enviar una transacción por cada log (ineficiente), agrupa los eventos en lotes (batch) de tamaño configurable (ej. 5 logs). Construye un Árbol de Merkle localmente y extrae únicamente la **Raíz (Merkle Root)**.
*   **Interacción Blockchain:** Firma y envía la transacción con la Merkle Root al Smart Contract mediante RPC.
*   **Persistencia de Pruebas:** Guarda localmente un archivo `merkle_proofs.json` que mapea cada Root con los logs originales, permitiendo la reconstrucción futura de la evidencia.

### 4.3.3. Smart Contract (LogAuditor.sol)
Desplegado en la red Ethereum, este componente es minimalista intencionalmente para reducir costes de ejecución (Gas).
*   **Estructura de Datos:** Mantiene un mapeo (`mapping(bytes32 => BatchInfo)`) donde la clave es el Hash Root del lote.
*   **Inmutabilidad:** Una vez que un lote es registrado mediante la función `submitBatch`, sus datos (Timestamp, Block Number) quedan sellados permanentemente y no pueden ser modificados ni por el administrador del contrato.

### 4.3.4. Interfaces y Verificación (Inspector & Web App)
Proporciona la "Prueba de Integridad" al usuario final.
*   **Verificador (Backend):** Algoritmo que lee el archivo de logs actual del disco, reconstruye los Árboles de Merkle desde cero y compara las Raíces resultantes con las almacenadas en la Blockchain.
*   **Dashboard Web:** Interfaz gráfica que muestra el estado del sistema ("Íntegro" vs "Comprometido").
    *   Muestra logs en tiempo real vía WebSocket/Pooling.
    *   En caso de discrepancia (Hash no coincidente), dispara una alerta visual y presenta el **vector de diferencia**, mostrando qué línea exacta fue modificada o borrada y recuperando su valor original desde el archivo de pruebas local.

## 4.4. Flujo de Información (Data Flow)

1.  **Ingesta:** El sistema operativo escribe una línea en el log.
2.  **Procesamiento:** El Middleware captura la línea y la añade a un buffer en memoria.
3.  **Hashing:** Cuando el buffer se llena, se genera el Árbol de Merkle.
4.  **Notarización:** La Raíz del árbol se envía a Ethereum (Ganache).
5.  **Verificación:** Bajo demanda, el auditor consulta la Blockchain y valida que los datos en disco coincidan matemáticamente con la Raíz guardada.
