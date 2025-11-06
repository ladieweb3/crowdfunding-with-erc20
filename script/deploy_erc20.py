from moccasin.boa_tools import VyperContract
from eth_utils import to_wei
from contracts import fund_token

INITIAL_SUPPLY = to_wei(1000, "ether")  

def deploy_fund_token()-> VyperContract:
    """
    Deploys a simple ERC20 token contract using Vyper.

    Returns:
        VyperContract: The deployed ERC20 token contract instance.
    """
    fund_token_contract = fund_token.deploy(INITIAL_SUPPLY)
    print(f"Fund Token deployed at: {fund_token_contract.address}")
    return fund_token_contract



def moccasin_main()-> VyperContract:
    """
    Main deployment function for Moccasin framework.

    Returns:
        VyperContract: The deployed ERC20 token contract instance.
    """
    return deploy_fund_token()