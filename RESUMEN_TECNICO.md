# Resumen Técnico del Proyecto: Sistema de Auditoría de Logs con Blockchain

## 1. Arquitectura del Sistema
El sistema sigue una arquitectura híbrida **Off-Chain / On-Chain** para garantizar escalabilidad y seguridad.

### Componentes Principales:
1.  **Fuente de Datos (Simulador):** Script Python que genera logs de tráfico web y accesos SSH simulando un entorno real (Honeypot).
2.  **Middleware (Agente de Anclaje):**
    *   Monitoriza el archivo de logs en tiempo real.
    *   Implementa una estructura de **Merkle Tree** para agrupar logs en lotes (Batching).
    *   Calcula el **Merkle Root** (Huella digital única del lote).
    *   Envía una transacción a la Blockchain (Ganache) solo con la Root, ahorrando costes de Gas.
    *   Genera una "Prueba de Existencia" (`merkle_proofs.json`) localmente para futuras verificaciones.
3.  **Smart Contract (Solidity):**
    *   Almacena las Roots de forma inmutable.
    *   Actúa como "Notario Digital" descentralizado.
4.  **Dashboard de Auditoría (Web Interface):**
    *   Interfaz visual para monitoreo en tiempo real.
    *   Motor de verificación que recalcula los hashes locales y los cruza con la Blockchain.
    *   Sistema de alerta ante manipulación de datos (Tampering Detection).

## 2. Tecnologías Utilizadas
*   **Blockchain:** Ethereum (Simulado con Ganache).
*   **Smart Contracts:** Solidity (v0.8.0).
*   **Backend:** Python 3.11 + Web3.py + Flask.
*   **Algoritmos:** HASHLIB (SHA-256) y Merkle Trees customizados.
*   **Frontend:** HTML5, JavaScript (Fetch API), TailwindCSS.

## 3. Justificación del Diseño (Merkle Trees)
En lugar de subir cada log individualmente a la Blockchain (lo cual sería lento y costoso), utilizamos Árboles de Merkle.
*   **Eficiencia O(1):** El coste de escritura en Blockchain es constante, independientemente de si el lote tiene 10 o 1000 logs. Solo se sube 1 Hash (32 bytes).
*   **Privacidad:** Los datos sensibles (IPs, usuarios) nunca salen del servidor local. Solo se publica su prueba criptográfica.
*   **Verificabilidad:** Permite demostrar matemáticamente que un log específico pertenece al lote anclado sin revelar el resto de la información.

## 4. Guía de Despliegue (Cómo probarlo)
1.  **Iniciar Blockchain Local:**
    *   Abrir Ganache y configurar en `HTTP://127.0.0.1:7545`.
2.  **Desplegar Contrato:**
    ```bash
    python scripts/deploy.py
    ```
3.  **Iniciar Simulador de Tráfico:**
    ```bash
    python scripts/creador_logs.py
    ```
4.  **Iniciar Middleware (Anclaje):**
    ```bash
    python src/middleware/middleware.py
    ```
5.  **Iniciar Dashboard y Verificar:**
    ```bash
    python src/web/app.py
    ```
    *   Abrir navegador en `http://localhost:5000`.

## 5. Caso de Uso: Detección de Intrusos
Si un atacante (`root`) modifica el archivo `/var/log/syslog` para borrar su rastro:
1.  El sistema de auditoría recalcula el Merkle Root con los datos actuales del disco.
2.  Compara este Root con el almacenado inmutablemente en el Smart Contract.
3.  Al no coincidir, identifica el lote corrupto y utiliza el archivo de respaldo (`merkle_proofs.json`) para restaurar y mostrar la evidencia original que el atacante intentó eliminar.
