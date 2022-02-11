import os
import sys
import json
import logging
import argparse

from dotenv import load_dotenv
from pathlib import Path
from web3 import Web3
from ens import ENS
from collections import defaultdict
from eth_utils import is_address

ERC20_ABI_JSON = '[{"constant": true, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "payable": false, "type": "function"}, {"constant": false, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "success", "type": "bool"}], "payable": false, "type": "function"}, {"constant": true, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "payable": false, "type": "function"}, {"constant": false, "inputs": [{"name": "_from", "type": "address"}, {"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transferFrom", "outputs": [{"name": "success", "type": "bool"}], "payable": false, "type": "function"}, {"constant": true, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "payable": false, "type": "function"}, {"constant": true, "inputs": [], "name": "version", "outputs": [{"name": "", "type": "string"}], "payable": false, "type": "function"}, {"constant": true, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "payable": false, "type": "function"}, {"constant": true, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "payable": false, "type": "function"}, {"constant": false, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "success", "type": "bool"}], "payable": false, "type": "function"}, {"constant": false, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}, {"name": "_extraData", "type": "bytes"}], "name": "approveAndCall", "outputs": [{"name": "success", "type": "bool"}], "payable": false, "type": "function"}, {"constant": true, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "remaining", "type": "uint256"}], "payable": false, "type": "function"}, {"inputs": [{"name": "_initialAmount", "type": "uint256"}, {"name": "_tokenName", "type": "string"}, {"name": "_decimalUnits", "type": "uint8"}, {"name": "_tokenSymbol", "type": "string"}], "type": "constructor"}, {"payable": false, "type": "fallback"}, {"anonymous": false, "inputs": [{"indexed": true, "name": "_from", "type": "address"}, {"indexed": true, "name": "_to", "type": "address"}, {"indexed": false, "name": "_value", "type": "uint256"}], "name": "Transfer", "type": "event"}, {"anonymous": false, "inputs": [{"indexed": true, "name": "_owner", "type": "address"}, {"indexed": true, "name": "_spender", "type": "address"}, {"indexed": false, "name": "_value", "type": "uint256"}], "name": "Approval", "type": "event"}]'
ERC20_ABI = json.loads(ERC20_ABI_JSON)

logger = logging.getLogger()


def get_token_decimals(w3, address):
    contract = w3.eth.contract(address=address, abi=ERC20_ABI)
    return contract.functions.decimals().call()


def get_token_symbol(w3, address):
    contract = w3.eth.contract(address=address, abi=ERC20_ABI)
    return contract.functions.symbol().call()


def get_token_owners(w3, address, from_block=0):

    BLACKHOLE = "0x0000000000000000000000000000000000000000"

    # HASH OF STANDARD ERC20 Transfer(address,address,amount)
    TRANSFER_HASH = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

    # GET TRANSACTIONS
    logs = w3.eth.get_logs(
        {
            "address": address,
            "fromBlock": from_block,
            "topics": [TRANSFER_HASH],
        }
    )

    txs = []
    for log in logs:
        tx = {
            "from": w3.toChecksumAddress(log["topics"][1].hex()[-40:]),
            "to": w3.toChecksumAddress(log["topics"][2].hex()[-40:]),
            "amount": int(log.get("data"), 16),
        }
        txs.append(tx)

    # CALCULATE BALANCES
    balances = defaultdict(lambda: 0)
    for tx in txs:
        balances[str(tx["from"])] -= tx["amount"]
        balances[tx["to"]] += tx["amount"]

    if BLACKHOLE in balances:
        del balances[BLACKHOLE]

    accounts = [{"address": k, "amount": balances[k]} for k in balances]
    accounts = sorted(accounts, key=lambda a: a["amount"], reverse=True)

    return accounts


def main():
    """
    Generates a json file containing all of the members of a dao by searching the blockchain for token holders.

    Usage: python daois.py [contract_address]
    """

    load_dotenv()

    parser = argparse.ArgumentParser(description="Scan blockchain for token holders")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--ens", action="store_true")
    parser.add_argument("address", help="Contract address for ERC20 token")
    args = parser.parse_args()

    ETHEREUM_NODE = os.environ.get("ETHEREUM_NODE")
    DEBUG = args.debug
    FETCH_DOMAINS = args.ens
    TOKEN_ADDRESS = args.address

    logging.basicConfig(level=(DEBUG and logging.DEBUG or logging.INFO))

    if not ETHEREUM_NODE:
        exit("ETHEREUM_NODE must be set in ENV VARS")

    if not is_address(TOKEN_ADDRESS):
        exit("INVALID TOKEN ADDRESS")

    w3 = Web3(Web3.HTTPProvider(ETHEREUM_NODE))

    TOKEN_ADDRESS = w3.toChecksumAddress(TOKEN_ADDRESS)
    logger.info("TOKEN ADDRESS: {}".format(TOKEN_ADDRESS))

    TOKEN_DECIMALS = get_token_decimals(w3, TOKEN_ADDRESS)
    logger.info("TOKEN DECIMALS: {}".format(TOKEN_DECIMALS))

    TOKEN_SYMBOL = get_token_symbol(w3, TOKEN_ADDRESS)
    logger.info("TOKEN SYMBOL: {}".format(TOKEN_SYMBOL))

    accounts = get_token_owners(w3, TOKEN_ADDRESS)
    logger.info("TOKEN HOLDERS: {}".format(len(accounts)))

    logger.debug("CONVERTING AMOUNTS TO {} DECIMALS".format(TOKEN_DECIMALS))
    for i in range(len(accounts)):
        accounts[i]["amount"] = int(accounts[i]["amount"]) / (10 ** TOKEN_DECIMALS)

    if FETCH_DOMAINS:
        logger.info("FETCHING ENS DOMAINS FOR ACCOUNTS")
        ns = ENS.fromWeb3(w3)
        for i in range(len(accounts)):
            accounts[i]["domain"] = ns.name(accounts[i]["address"])
            logger.info(
                "ENS NAME:{}:{}".format(accounts[i]["address"], accounts[i]["domain"])
            )

    filepath = Path("data/%s/members.json" % TOKEN_ADDRESS)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        f.write(json.dumps(accounts, indent=4, sort_keys=True))
    logger.info("MEMBERS WRITTEN TO: {}".format(filepath))

if __name__ == "__main__":
    main()
