from moccasin.boa_tools import VyperContract
from moccasin.config import get_active_network

from contracts import crowdfunding


def deploy_crowdfunding(erc20_token: VyperContract) -> VyperContract:
    """
    Deploys a crowdfunding contract using Vyper.

    Returns:
        VyperContract: The deployed crowdfunding contract instance.
    """
    crowdfund : VyperContract = crowdfunding.deploy(erc20_token)
    active_network = get_active_network()
    if active_network.has_explorer() and active_network.is_local_or_forked_network() is False:
        result = active_network.moccasin_verify(crowdfund)
        result.wait_for_verification()

    print(f"Contract deployed to {crowdfund.address}")
    return crowdfund


def moccasin_main() -> VyperContract:
    """
    Main deployment function for Moccasin framework.

    Returns:
        VyperContract: The deployed crowdfunding contract instance.
    """
    active_network = get_active_network()
    fund_token: VyperContract = active_network.manifest_named("fund_token")
    print(f"network: {active_network.name} , using price feed at {fund_token.address}")
    return deploy_crowdfunding(fund_token.address)