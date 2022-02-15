# DAOIS lookup

DAOIS (pronouced: "Dao is" like "who is") is a simple tool for querying ethereum for a list of current token holders and their associated ENS domains.  The script can be installed and run locally, however, it is primaraly designed to be run via github actions to keep a current cache of DAOs that you might want to track the membership of.


## Run Locally

Add an ```ETHEREUM_NODE``` to your environment either manually or by adding a ```.env``` file to this folder.
```
ETHEREUM_NODE = "https://mainnet.infura.io/v3/1234567890"
```

```
pip install web3
pip install python-dotenv
python daois.py {ERC20 contract address} --ens
```


## Run via GitHub Actions

To run via GitHub Actions, you will need to fork the project and then add a valid ethereum node as a repository secret called ```ETHEREUM_NODE```.

Once this is in place you can simply go to **Actions** and select **Adhoc DAO Member Fetch** and click **Run workflow** where you will be promped for the ERC20 contract address of the token you would like to pull holder data for.

When the action is complete you will see a subfolder with the ERC20 address in [./data](./data) and it will contain ```members.json``` and ```info.json```


## Run daily via GitHub Actions

If you would like to keep track of changes and updates to token holders on a schedule (like once per day), you can add a workflow with a cron event similar to the one below.

```
name: MyDAO Members
on:
  schedule:
    - cron: "0 5 * * *"
  workflow_dispatch:
jobs:
  betadao:
    uses: {{your_github_user}}/daois/.github/workflows/holders.yml@main
    with:
      address: "{{valid_erc20_token_address}}"
    secrets:
      ETHEREUM_NODE: ${{secrets.ETHEREUM_NODE}}
```
