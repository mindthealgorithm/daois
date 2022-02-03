# DAOIS lookup

Query the ethereum blockchain for a list of DAO token holders and ENS profiles.

## Setup

Add an ```ETHEREUM_NODE``` to your environment either manually or by adding a ```.env``` file to this folder.
```
ETHEREUM_NODE = "https://mainnet.infura.io/v3/1234567890"
```

## Run Locally
```
poetry install
poetry shell
python members.py {ERC20 contract address]}
```
