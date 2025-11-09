import boa
from eth_utils import to_wei

from tests.conftest import CREATOR, SEND_VALUE

FUNDER = boa.env.generate_address("funder")
RANDOM_USER = boa.env.generate_address("no_owner")


def days(n):
    """
    @notice Convert days to future timestamp
    @param n Number of days from now
    @return Future timestamp
    """
    return 86400 * n


def test_CreateCampaign(crowdfund):
    """Testing the creation of a campaign"""
    with boa.env.prank(CREATOR):
        campaign_id = crowdfund.createCampaigns(
            CREATOR,
            "Test Campaign",
            "This is a test campaign",
            to_wei(10, "ether"),
            boa.env.timestamp + days(1),  # startAt in 1 day
            boa.env.timestamp + days(30),  # endAt in 30 days
            "https://example.com/image.png",
        )

    assert campaign_id == 1
    campaign = crowdfund.s_campaigns(campaign_id)
    assert campaign.creator == CREATOR
    assert campaign.name == "Test Campaign"
    assert campaign.description == "This is a test campaign"
    assert campaign.goal == to_wei(10, "ether")
    assert campaign.startAt == boa.env.timestamp + days(1)
    assert campaign.endAt == boa.env.timestamp + days(30)
    assert campaign.image == "https://example.com/image.png"


def test_CreateCampaign_RevertsWhen_EndAtIsNotInFuture(crowdfund):
    """Testing campaign creation fails when endAt is not in the future"""
    with boa.env.prank(CREATOR):
        with boa.reverts("End time must be after start time"):
            crowdfund.createCampaigns(
                CREATOR,
                "Test Campaign",
                "This is a test campaign",
                to_wei(10, "ether"),
                boa.env.timestamp + days(60),  # startAt in 1 minute
                boa.env.timestamp + days(30),  # endAt before startAt
                "https://example.com/image.png",
            )


def test_CreateMultipleCampaigns_UpdatesCreator_MappingCorrectly(crowdfund):
    """Testing that creating multiple campaigns updates the creator mapping correctly"""
    with boa.env.prank(CREATOR):
        campaign_id1 = crowdfund.createCampaigns(
            CREATOR,
            "Campaign 1",
            "First campaign",
            to_wei(5, "ether"),
            boa.env.timestamp + days(1),
            boa.env.timestamp + days(30),
            "https://example.com/image1.png",
        )
        campaign_id2 = crowdfund.createCampaigns(
            CREATOR,
            "Campaign 2",
            "Second campaign",
            to_wei(15, "ether"),
            boa.env.timestamp + days(2),
            boa.env.timestamp + days(32),
            "https://example.com/image2.png",
        )

    assert campaign_id1 == 1
    assert campaign_id2 == 2

    campaign1 = crowdfund.s_campaigns(campaign_id1)
    campaign2 = crowdfund.s_campaigns(campaign_id2)

    assert campaign1.creator and campaign2.creator == CREATOR
    assert len(crowdfund.getCampaignsCreatedByCreator(CREATOR)) == 2
    assert crowdfund.getTotalCampaigns() == 2


def test_CreateCampaign_EmitsCorrectEvent(crowdfund):
    """Testing that campaign creation emits the correct event"""
    with boa.env.prank(CREATOR):
        crowdfund.createCampaigns(
            CREATOR,
            "Event Test Campaign",
            "Testing event emission",
            to_wei(20, "ether"),
            boa.env.timestamp + days(1),
            boa.env.timestamp + days(30),
            "https://example.com/event_image.png",
        )

    logs = crowdfund.get_logs()
    log_campaign_created = [
        log for log in logs if type(log).__name__ == "CampaignCreated"
    ]
    for log in log_campaign_created:
        assert log.creator == CREATOR
        assert log.goal == to_wei(20, "ether")
        assert log.startAt == boa.env.timestamp + days(1)
        assert log.endAt == boa.env.timestamp + days(30)


def test_FundCampaign_Successfully(campaign_created, crowdfund, fund_token, account):
    """Testing funding a campaign successfully"""
    # Give tokens to the funder
    with boa.env.prank(account.address):
        fund_token.transfer(FUNDER, SEND_VALUE)

    # Advance time for the campaign to be active
    campaign = crowdfund.s_campaigns(campaign_created)
    target_time = campaign.startAt - boa.env.timestamp + 86400
    boa.env.time_travel(seconds=target_time)

    # ===== ACT =====
    with boa.env.prank(FUNDER):
        fund_token.approve(crowdfund.address, SEND_VALUE)
        crowdfund.fundCampaign(campaign_created, SEND_VALUE)

    # ===== ASSERT =====

    campaign_after_funds = crowdfund.s_campaigns(campaign_created)
    assert campaign_after_funds.amountCollected == SEND_VALUE
    assert (
        crowdfund.getAddressToAmountFundedByCampaign(campaign_created, FUNDER)
        == SEND_VALUE
    )
    assert len(crowdfund.getFundersOfCampaign(campaign_created)) == 1


def test_MultipleFunders_FundCampaign_Successfully(
    campaign_created, crowdfund, fund_token, account
):
    """Testing funding a campaign by multiple funders successfully"""
    # Give tokens to the funders
    funders = [boa.env.generate_address(f"funder_{i}") for i in range(5)]
    for funder in funders:
        with boa.env.prank(account.address):
            fund_token.transfer(funder, SEND_VALUE)

    # Advance time for the campaign to be active
    campaign = crowdfund.s_campaigns(campaign_created)
    target_time = campaign.startAt - boa.env.timestamp + 86400
    boa.env.time_travel(seconds=target_time)

    # ===== ACT =====
    for funder in funders:
        with boa.env.prank(funder):
            fund_token.approve(crowdfund.address, SEND_VALUE)
            crowdfund.fundCampaign(campaign_created, SEND_VALUE)

    # ===== ASSERT =====
    campaign_after_funds = crowdfund.s_campaigns(campaign_created)
    assert campaign_after_funds.amountCollected == SEND_VALUE * len(funders)

    for funder in funders:
        assert (
            crowdfund.getAddressToAmountFundedByCampaign(campaign_created, funder)
            == SEND_VALUE
        )

    assert len(crowdfund.getFundersOfCampaign(campaign_created)) == len(funders)


def test_FundCampaign_EmitsCorrectEvent(
    campaign_created, crowdfund, fund_token, account
):
    """Testing that funding a campaign emits the correct event"""
    # Give tokens to the funder
    with boa.env.prank(account.address):
        fund_token.transfer(FUNDER, SEND_VALUE)

    # Advance time for the campaign to be active
    campaign = crowdfund.s_campaigns(campaign_created)
    target_time = campaign.startAt - boa.env.timestamp + 86400
    boa.env.time_travel(seconds=target_time)

    # ===== ACT =====
    with boa.env.prank(FUNDER):
        fund_token.approve(crowdfund.address, SEND_VALUE)
        crowdfund.fundCampaign(campaign_created, SEND_VALUE)

    # ===== ASSERT =====
    logs = crowdfund.get_logs()
    log_campaign_funded = [
        log for log in logs if type(log).__name__ == "CampaignFunded"
    ]
    for log in log_campaign_funded:
        assert log.funders == FUNDER
        assert log.amount == SEND_VALUE


def test_OnlyCampaignOwner_CanClaimFunds(campaign_funded, crowdfund):
    """Testing that only the campaign owner can claim funds"""
    with boa.env.prank(RANDOM_USER):
        with boa.reverts("Only the creator can claim funds"):
            crowdfund.claimFunds(campaign_funded)


def test_CampaignOwner_CanClaimFunds_Successfully(
    campaign_funded, crowdfund, fund_token
):
    """Testing that the campaign owner can successfully claim funds"""
    campaign = crowdfund.s_campaigns(campaign_funded)
    campaign_creator = campaign.creator
    creator_initial_balance = fund_token.balanceOf(campaign_creator)

    target_time = campaign.endAt - boa.env.timestamp + days(1)
    boa.env.time_travel(seconds=target_time)
    # ===== ACT =====
    with boa.env.prank(campaign_creator):
        crowdfund.claimFunds(campaign_funded)

    # ===== ASSERT =====

    campaign_after = crowdfund.s_campaigns(campaign_funded)

    assert campaign_after.amountCollected == 0
    creator_final_balance = fund_token.balanceOf(campaign_creator)
    assert creator_final_balance - creator_initial_balance == SEND_VALUE * 25
    assert campaign_after.claimedByOwner is True


def test_FailedToClaimFunds_RevertsWhen_CampaignDidNotReachGoal(
    crowdfund, campaign_created, fund_token, account
):
    """Testing that claiming funds fails when the campaign did not reach its goal"""
    # Give tokens to the funder
    with boa.env.prank(account.address):
        fund_token.transfer(FUNDER, SEND_VALUE)

    # Advance time for the campaign to be active
    boa.env.time_travel(seconds=8640)

    # ===== ACT =====
    with boa.env.prank(FUNDER):
        fund_token.approve(crowdfund.address, SEND_VALUE)
        crowdfund.fundCampaign(campaign_created, SEND_VALUE)

    # ===== ASSERT =====
    campaign = crowdfund.s_campaigns(campaign_created)

    target_time = campaign.endAt - boa.env.timestamp + days(1)
    boa.env.time_travel(seconds=target_time)
    with boa.env.prank(campaign.creator):
        with boa.reverts("Campaign did not reach its goal"):
            crowdfund.claimFunds(campaign_created)


def test_FailedToClaimRevertsWhen_CalledBefore_CampaignEnds(campaign_funded, crowdfund):
    """Testing that claiming fails when called before the campaign ends"""
    campaign = crowdfund.s_campaigns(campaign_funded)
    campaign_creator = campaign.creator

    target_time = campaign.endAt - boa.env.timestamp - days(1)
    boa.env.time_travel(seconds=target_time)

    with boa.env.prank(campaign_creator):
        with boa.reverts("Campaign not ended"):
            crowdfund.claimFunds(campaign_funded)


def test_FailedToClaimFunds_RevertsWhen_AlreadyClaimed(campaign_funded, crowdfund):
    """Testing that claiming funds fails when it has already been claimed"""
    campaign = crowdfund.s_campaigns(campaign_funded)
    campaign_creator = campaign.creator

    target_time = campaign.endAt - boa.env.timestamp + days(1)
    boa.env.time_travel(seconds=target_time)
    # First claim
    with boa.env.prank(campaign_creator):
        crowdfund.claimFunds(campaign_funded)

    # Second claim should revert
    with boa.env.prank(campaign_creator):
        with boa.reverts("Funds already claimed"):
            crowdfund.claimFunds(campaign_funded)


def test_ClaimFunds_EmitsCorrectEvent(campaign_funded, crowdfund):
    """Testing that claiming funds emits the correct event"""
    campaign = crowdfund.s_campaigns(campaign_funded)
    campaign_creator = campaign.creator

    target_time = campaign.endAt - boa.env.timestamp + days(1)
    boa.env.time_travel(seconds=target_time)

    # ===== ACT =====
    with boa.env.prank(campaign_creator):
        crowdfund.claimFunds(campaign_funded)

    # ===== ASSERT =====
    logs = crowdfund.get_logs()
    log_campaign_amount_claimed = [
        log for log in logs if type(log).__name__ == "CampaignAmountClaimed"
    ]
    for log in log_campaign_amount_claimed:
        assert log.creator == campaign_creator
        assert log.amount == SEND_VALUE * 25
