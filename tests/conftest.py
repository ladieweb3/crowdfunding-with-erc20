import boa
import pytest
from eth_utils import to_wei
from moccasin.config import get_active_network

from script.deploy import deploy_crowdfunding
from script.deploy_erc20 import deploy_fund_token

CREATOR = boa.env.generate_address("creator")
SEND_VALUE = to_wei(1, "ether")


@pytest.fixture(scope="session")
def account():
    return get_active_network().get_default_account()


@pytest.fixture(scope="session")
def fund_token():
    return deploy_fund_token()


@pytest.fixture(scope="function")
def crowdfund(fund_token):
    return deploy_crowdfunding(fund_token)


@pytest.fixture(scope="function")
def campaign_created(crowdfund):
    # Utiliser get_timestamp() pour avoir le temps actuel
    current_time = boa.env.timestamp

    with boa.env.prank(CREATOR):
        campaign_id = crowdfund.createCampaigns(
            CREATOR,
            "Fixture Campaign",
            "This is a fixture campaign",
            to_wei(10, "ether"),
            current_time + 60,  # startAt dans 1 minute
            current_time + (30 * 86400),  # endAt dans 30 jours
            "https://example.com/image.png",
        )
    return campaign_id


@pytest.fixture(scope="function")
def campaign_funded(crowdfund, campaign_created, account, fund_token):
    funders = [boa.env.generate_address(f"funder_{i}") for i in range(25)]
    for funder in funders:
        with boa.env.prank(account.address):
            fund_token.transfer(funder, SEND_VALUE)

    # Avance le temps pour que la campagne soit active
    boa.env.time_travel(seconds=8640)

    # ===== ACT =====
    for funder in funders:
        with boa.env.prank(funder):
            fund_token.approve(crowdfund.address, SEND_VALUE)
            crowdfund.fundCampaign(campaign_created, SEND_VALUE)
    return campaign_created
