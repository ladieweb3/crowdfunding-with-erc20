import boa
from boa.util.abi import Address
from eth.constants import ZERO_ADDRESS
from eth_utils import to_wei
from hypothesis import assume, settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
)
from moccasin.config import get_active_network

from script.deploy import deploy_crowdfunding
from script.deploy_erc20 import deploy_fund_token

FUNDERS_SIZE = 10


class CrowdfundingStateFuzzer(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()

    @initialize()
    def setup(self):
        self.fund_token = deploy_fund_token()
        self.crowdfund = deploy_crowdfunding(self.fund_token)
        self.creator = boa.env.generate_address()
        self.deployer = get_active_network().get_default_account()

        # Préparer une liste d'adresses de funders
        self.funders = []
        while len(self.funders) < FUNDERS_SIZE:
            funder = boa.env.generate_address()
            if funder != Address("0x" + ZERO_ADDRESS.hex()):
                self.funders.append(funder)

        self.campaign_ids = []

    @rule(
        goal=st.integers(min_value=1, max_value=10),
    )
    def create_campaign(self, goal):
        """Create a new crowdfunding campaign"""
        current_time = boa.env.timestamp
        goal_wei = to_wei(goal, "ether")

        with boa.env.prank(self.creator):
            campaign_id = self.crowdfund.createCampaigns(
                self.creator,
                "Dogs Token",
                "A campaign to fund a new ERC20 token for dog lovers.",
                goal_wei,
                current_time + 60,
                current_time + 86400,
                "https://example.com/image.png",
            )
            self.campaign_ids.append(campaign_id)

    @rule(amount=st.integers(min_value=1, max_value=50))
    def fund_campaign(self, amount):
        """Fund a crowdfunding campaign"""
        if not self.campaign_ids:
            return

        campaign_id = self.campaign_ids[-1]
        amount_wei = to_wei(amount, "ether")

        for funder in self.funders:
            with boa.env.prank(self.deployer.address):
                self.fund_token.transfer(funder, amount_wei)

        campaign = self.crowdfund.s_campaigns(campaign_id)
        current_time = boa.env.timestamp
        time_to_advance = int(campaign.startAt - current_time + 1)
        boa.env.time_travel(seconds=time_to_advance)

        for funder in self.funders:
            with boa.env.prank(funder):
                self.fund_token.approve(self.crowdfund.address, amount_wei)
                self.crowdfund.fundCampaign(campaign_id, amount_wei)

        campaign_after = self.crowdfund.s_campaigns(campaign_id)
        print(
            f"✅ All funders have funded campaign {campaign_id} with {amount_wei} each, goal: {campaign_after.goal} , collected: {campaign_after.amountCollected}"
        )

    @rule()
    def claim_campaign_funds_errors(self):
        """The creator claims the funds from the campaign"""
        assume(len(self.campaign_ids) > 0)  # Assume there is at least one campaign

        campaign_id = self.campaign_ids[-1]

        campaign = self.crowdfund.s_campaigns(campaign_id)
        target_time = campaign.endAt - boa.env.timestamp + 86400
        boa.env.time_travel(seconds=target_time)

        with boa.env.prank(campaign.creator):
            # ✅ Accept reverts — normal behavior
            try:
                self.crowdfund.claimFundsWithoutZeroing(campaign_id)
            except boa.BoaError:
                pass

        campaign_after_claim = self.crowdfund.s_campaigns(campaign_id)
        
        print(
            f"✅ The creator has claimed the funds from campaign {campaign_id}, goal: {campaign_after_claim.goal} , collected: {campaign_after_claim.amountCollected}"
        )

    @invariant()
    def invariant_after_claim_amount_is_zero(self):
        """ If a campaign is claimed, then getAmountCollected(campaign_id) must be 0.
        Iterate over all known campaigns (if none, do nothing). 
        """
        if not self.campaign_ids:
            return  # nothing to check

        for campaign_id in list(self.campaign_ids):
            # safe read: skip invalid ids (défensif)
            try:
                claimed = self.crowdfund.s_campaigns(campaign_id).claimedByOwner
            except Exception:
                continue

            if claimed:
                collected = self.crowdfund.getAmountCollected(campaign_id)
                assert collected == 0, (
                    f"[BUG] Campaign {campaign_id} claimedByOwner=True but amountCollected={collected}, expected 0"
                )


crowdfunding_state_fuzzer = CrowdfundingStateFuzzer.TestCase
crowdfunding_state_fuzzer.settings = settings(max_examples=100, stateful_step_count=50)
