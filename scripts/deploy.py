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

ganache_url = os.getenv("GANACHE_URL")
web3 = Web3(Web3.HTTPProvider(ganache_url))
chain_id = 1337
private_key = os.getenv("PRIVATE_KEY")
my_address = web3.eth.account.from_key(private_key).address

print("Conexión exitosa")
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

print("[*] Desplegando en Ganache...")

LogAuditor = web3.eth.contract(abi=abi, bytecode=bytecode)
nonce = web3.eth.get_transaction_count(my_address)


transaction = LogAuditor.constructor().build_transaction({
    "chainId": chain_id,
    "gasPrice": web3.eth.gas_price,
    "from": my_address,
    "nonce": nonce
})

signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)

# Enviar transacción firmada a la red
tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
print(f"    Tx Hash: {web3.to_hex(tx_hash)}")

tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
print(f"[+] ¡Contrato desplegado! Dirección: {tx_receipt.contractAddress}")

config_data = {
    "contract_address": tx_receipt.contractAddress,
    "abi": abi
}

with open(CONFIG_PATH, "w") as f:
    json.dump(config_data, f)
print(f"[*] Configuración guardada en '{CONFIG_PATH}'")
