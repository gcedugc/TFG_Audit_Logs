import json
from web3 import Web3
from solcx import compile_standard, install_solc
import os
from dotenv import load_dotenv

# Directorio base: este script está en scripts/, el padre es la raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Cargar variables de entorno
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Rutas
CONTRACT_PATH = os.path.join(BASE_DIR, "src", "contracts", "LogAuditor.sol")
CONFIG_PATH = os.path.join(BASE_DIR, "contract_config.json")

# RPC_URL lo establece start.py; si no existe, usar GANACHE_URL como fallback
rpc_url = os.getenv("RPC_URL") or os.getenv("GANACHE_URL")
web3 = Web3(Web3.HTTPProvider(rpc_url))
chain_id = web3.eth.chain_id
private_key = os.getenv("PRIVATE_KEY")
my_address = web3.eth.account.from_key(private_key).address

is_local = "127.0.0.1" in rpc_url or "localhost" in rpc_url
network_name = "Ganache (local)" if is_local else f"Sepolia (Chain ID: {chain_id})"

print(f"Conexión exitosa — {network_name}")
print("Cuenta:", my_address)

install_solc("0.8.0")

if not os.path.exists(CONTRACT_PATH):
    print(f"Error: No se encuentra el contrato en {CONTRACT_PATH}")
    exit(1)

with open(CONTRACT_PATH, "r") as file:
    log_auditor_file = file.read()

compiled_sol = compile_standard(
    {
        "language": "Solidity",
        "sources": {"LogAuditor.sol": {"content": log_auditor_file}},
        "settings": {
            "outputSelection": {
                "*": {"*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]}
            }
        },
    },
    solc_version="0.8.0",
)

bytecode = compiled_sol["contracts"]["LogAuditor.sol"]["LogAuditor"]["evm"]["bytecode"]["object"]
abi = compiled_sol["contracts"]["LogAuditor.sol"]["LogAuditor"]["abi"]

print(f"[*] Desplegando en {network_name}...")

LogAuditor = web3.eth.contract(abi=abi, bytecode=bytecode)
nonce = web3.eth.get_transaction_count(my_address)

# Construir transacción con gas compatible (EIP-1559 para Sepolia, legacy para Ganache)
tx_params = {
    "chainId": chain_id,
    "from": my_address,
    "nonce": nonce,
}

if is_local:
    tx_params["gasPrice"] = web3.eth.gas_price
else:
    # EIP-1559: usar maxFeePerGas y maxPriorityFeePerGas
    latest_block = web3.eth.get_block("latest")
    base_fee = latest_block.get("baseFeePerGas", 0)
    tx_params["maxFeePerGas"] = base_fee * 2 + web3.to_wei(2, "gwei")
    tx_params["maxPriorityFeePerGas"] = web3.to_wei(2, "gwei")

transaction = LogAuditor.constructor().build_transaction(tx_params)

signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)

# Enviar transacción firmada a la red
tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
print(f"    Tx Hash: {web3.to_hex(tx_hash)}")

if not is_local:
    print("    Esperando confirmación en Sepolia (puede tardar ~15s)...")

tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
print(f"[+] ¡Contrato desplegado! Dirección: {tx_receipt.contractAddress}")

if not is_local:
    print(f"    Ver en Etherscan: https://sepolia.etherscan.io/address/{tx_receipt.contractAddress}")

config_data = {
    "contract_address": tx_receipt.contractAddress,
    "abi": abi
}

with open(CONFIG_PATH, "w") as f:
    json.dump(config_data, f)
print(f"[*] Configuración guardada en '{CONFIG_PATH}'")
