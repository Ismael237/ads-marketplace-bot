from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider
from config import TRON_API_URL, TRON_PRIVATE_KEY
import requests
from utils.logger import get_logger

logger = get_logger("tron_client")

tron = Tron(HTTPProvider(TRON_API_URL))

class TronClient:
    def __init__(self, api_url: str):
        self._tron = Tron(HTTPProvider(api_url))

    def address_from_private_key_hex(self, private_key_hex: str) -> str:
        priv = PrivateKey(bytes.fromhex(private_key_hex))
        return priv.public_key.to_base58check_address()

    def generate_wallet(self):
        priv = PrivateKey.random()
        address = priv.public_key.to_base58check_address()
        return {"address": address, "private_key": priv.hex()}

    def transfer_trx(self, from_private_key_hex: str, to_address: str, amount_trx: float) -> str:
        priv = PrivateKey(bytes.fromhex(from_private_key_hex))
        from_address = priv.public_key.to_base58check_address()
        txn = (
            self._tron.trx.transfer(from_address, to_address, int(amount_trx * 1_000_000))
            .build()
            .sign(priv)
        )
        result = txn.broadcast().wait()
        return result.get("id") if isinstance(result, dict) else result

    def get_account_balance(self, address: str) -> float:
        return self._tron.get_account_balance(address)

    def get_transaction_info(self, tx_hash: str):
        try:
            return self._tron.get_transaction_info(tx_hash)
        except Exception as exc:
            logger.error(f"get_transaction_info failed for {tx_hash}: {exc}")
            return None

    def get_confirmations(self, block_number: int):
        try:
            latest = self._tron.get_latest_block().get("block_header", {}).get("raw_data", {}).get("number")
            if latest is None or block_number is None:
                return None
            return int(latest) - int(block_number)
        except Exception as exc:
            logger.error(f"get_confirmations failed: {exc}")
            return None

    def list_incoming_trx(self, address: str):
        try:
            url = f"{TRON_API_URL}/v1/accounts/{address}/transactions?limit=50&only_to=true&sort=-timestamp"
            headers = {"accept": "application/json"}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                transactions = []
                for tx in data.get('data', []):
                    if tx.get('raw_data', {}).get('contract', [{}])[0].get('type') == 'TransferContract':
                        contract = tx['raw_data']['contract'][0]['parameter']['value']
                        transactions.append({
                            'txID': tx['txID'],
                            'from': contract.get('owner_address'),
                            'to': contract.get('to_address'),
                            'amount': contract.get('amount'),
                            'confirmations': 20 if tx.get('ret', [{}])[0].get('contractRet') == 'SUCCESS' else 0
                        })
                return transactions
            else:
                logger.error(f"TronGrid API error: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"list_incoming_trx error: {e}")
            return []

_client: TronClient | None = None

def get_tron_client() -> TronClient:
    global _client
    if _client is None:
        _client = TronClient(TRON_API_URL)
    return _client

def get_main_wallet():
    priv_key = PrivateKey(bytes.fromhex(TRON_PRIVATE_KEY))
    address = priv_key.public_key.to_base58check_address()
    return address, priv_key

def address_from_private_key_hex(private_key_hex: str) -> str:
    return get_tron_client().address_from_private_key_hex(private_key_hex)

def generate_wallet():
    priv = PrivateKey.random()
    address = priv.public_key.to_base58check_address()
    return address, priv.hex()

def get_trx_transactions(address):
    try:
        url = f"{TRON_API_URL}/v1/accounts/{address}/transactions?limit=50&only_to=true&sort=-timestamp"
        headers = {
            "accept": "application/json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            transactions = []
            for tx in data.get('data', []):
                # Vérifier que c'est un transfert de TRX
                if tx.get('raw_data', {}).get('contract', [{}])[0].get('type') == 'TransferContract':
                    contract = tx['raw_data']['contract'][0]['parameter']['value']
                    transactions.append({
                        'txID': tx['txID'],
                        'from': contract.get('owner_address'),
                        'to': contract.get('to_address'),
                        'amount': contract.get('amount'),
                        'confirmations': tx.get('ret', [{}])[0].get('contractRet') == 'SUCCESS' and 20 or 0  # Hypothèse
                    })
            return transactions
        else:
            logger.error(f"Erreur API TronGrid: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"Erreur dans get_trx_transactions: {e}")
        return []

def send_trx(from_privkey_hex, to_address, amount):
    priv = PrivateKey(bytes.fromhex(from_privkey_hex))
    address = priv.public_key.to_base58check_address()
    txn = (
        tron.trx.transfer(address, to_address, int(amount * 1_000_000))
        .build()
        .sign(priv)
    )
    result = txn.broadcast().wait()
    return result['id']

def get_trx_balance(address):
    return tron.get_account_balance(address)