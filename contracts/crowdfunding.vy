# pragma version ^0.4.1
"""
@license MIT
@title crowdfunding
@author You!
@notice This is my crowdfunding contract!
"""

from interfaces import FundTokenInterface

# ------------------------------------------------------------------
#                        TYPE DECLARATIONS
# ------------------------------------------------------------------

struct Campaign:
    creator: address
    name: String[25]
    description: String[100]
    goal: uint256
    amountCollected: uint256
    startAt: uint256
    endAt: uint256
    image: String[100]
    funders: DynArray[address, 1000]
    claimedByOwner: bool


# ------------------------------------------------------------------
#                              EVENTS
# ------------------------------------------------------------------


event CampaignCreated:
    campaignId: indexed(uint256)
    creator: indexed(address)
    goal: uint256
    startAt: uint256
    endAt: uint256


event CampaignFunded:
    campaignId: indexed(uint256)
    funders: indexed(address)
    amount: uint256


event CampaignAmountClaimed:
    campaignId: indexed(uint256)
    creator: indexed(address)
    amount: uint256


I_TOKEN: public(immutable(FundTokenInterface))


# ------------------------------------------------------------------
#                        STORAGE VARIABLES
# ------------------------------------------------------------------

# Compteur de campagnes
s_campaignsCount: public(uint256)
# Mapping des campagnes par ID
s_campaigns: public(HashMap[uint256, Campaign])
# Mapping des financeurs par campagne (limité à 1000 financeurs)
s_fundersOfCampaign: public(HashMap[uint256, DynArray[address, 1000]])
# Mapping des campagnes créées par créateur (limité à 100 campagnes par créateur)
s_campaignCreatedByCreator: public(HashMap[address, DynArray[Campaign, 1000]])
# ReentrancyGuard
locked: bool
# Mapping du montant financé par adresse et par campagne
s_addressToAmountFundedByCampaign: public(
    HashMap[uint256, HashMap[address, uint256]]
)

# ------------------------------------------------------------------
#                           CONSTRUCTORS
# ------------------------------------------------------------------

@deploy
def __init__(_token: address):
    I_TOKEN = FundTokenInterface(_token)


# ------------------------------------------------------------------
#                            FUNCTIONS
# ------------------------------------------------------------------


@external
def createCampaigns(
    _creator: address,
    _name: String[25],
    _description: String[100],
    _goal: uint256,
    _startAt: uint256,
    _endAt: uint256,
    _image: String[100],
) -> uint256:
    """
    @notice Create a new crowdfunding campaign
    @param _creator The address of the campaign creator
    @param _name The name of the campaign
    @param _description The description of the campaign
    @param _goal The funding goal of the campaign
    @param _startAt The start time of the campaign (timestamp)
    @param _endAt The end time of the campaign (timestamp)
    @param _image The image URL of the campaign
    @return The ID of the created campaign
    """
    assert _startAt >= block.timestamp, "Start time must be in the future"
    assert _endAt > _startAt, "End time must be after start time"
    assert (
        _endAt <= block.timestamp + 90 * 86400
    ), "End time must be within 90 days"

    self.s_campaignsCount += 1
    campaign_id: uint256 = self.s_campaignsCount

    # Créer la nouvelle campagne
    new_campaign: Campaign = Campaign(
        creator=_creator,
        name=_name,
        description=_description,
        goal=_goal,
        amountCollected=0,
        startAt=_startAt,
        endAt=_endAt,
        image=_image,
        funders=[],  # Liste vide simplifiée
        claimedByOwner=False,
    )
    self.s_campaigns[campaign_id] = new_campaign

    self.s_campaignCreatedByCreator[msg.sender].append(new_campaign)

    log CampaignCreated(
        campaignId=campaign_id,
        creator=_creator,
        goal=_goal,
        startAt=_startAt,
        endAt=_endAt,
    )

    return campaign_id


@external
@nonreentrant
def fundCampaign(campaign_id: uint256, amount: uint256):
    """
    @notice Fund a crowdfunding campaign
    @param campaign_id The ID of the campaign to fund
    @param amount The amount of funds to contribute
    """

    campaign: Campaign = self.s_campaigns[campaign_id]

    # 1. Checks
    assert (
        campaign_id > 0 and campaign_id <= self.s_campaignsCount
    ), "Campaign does not exist"
    assert (
        block.timestamp >= campaign.startAt
        and block.timestamp <= campaign.endAt
    ), "Campaign is not active"
    assert amount > 0, "Amount must be greater than 0"

    # 2. Effects & 3. Interaction
    self.s_campaigns[campaign_id].amountCollected += amount
    extcall I_TOKEN.transferFrom(msg.sender, self, amount)
    self.s_addressToAmountFundedByCampaign[campaign_id][msg.sender] += amount
    self.s_fundersOfCampaign[campaign_id].append(msg.sender)

    # 4. Events
    log CampaignFunded(
        campaignId=campaign_id, funders=msg.sender, amount=amount
    )


@external
@nonreentrant
def claimFunds(campaign_id: uint256):
    """
    @notice Claim the collected funds for a successful campaign
    @param campaign_id The ID of the campaign to claim funds from
    """

    campaign: Campaign = self.s_campaigns[campaign_id]

    # 1. Checks
    assert (
        campaign_id > 0 and campaign_id <= self.s_campaignsCount
    ), "Campaign does not exist"
    assert campaign.creator == msg.sender, "Only the creator can claim funds"
    assert block.timestamp > campaign.endAt, "Campaign not ended"
    assert not campaign.claimedByOwner, "Funds already claimed"
    assert (
        campaign.amountCollected >= campaign.goal
    ), "Campaign did not reach its goal"

    # 2. Effects
    amount_to_transfer: uint256 = campaign.amountCollected
    self.s_campaigns[campaign_id].claimedByOwner = True
    self.s_campaigns[campaign_id].amountCollected = 0

    # 3. Interaction

    extcall I_TOKEN.transfer(campaign.creator, amount_to_transfer)

    # 4. Events
    log CampaignAmountClaimed(
        campaignId=campaign_id, creator=msg.sender, amount=amount_to_transfer
    )


@external
@nonreentrant
def claimFundsWithoutZeroing(campaign_id: uint256):
    """
    @notice Claim the collected funds for a successful campaign but without zeroing amountCollected
    @param campaign_id The ID of the campaign to claim funds from
    """

    campaign: Campaign = self.s_campaigns[campaign_id]

    # 1. Checks
    assert (
        campaign_id > 0 and campaign_id <= self.s_campaignsCount
    ), "Campaign does not exist"
    assert campaign.creator == msg.sender, "Only the creator can claim funds"
    assert block.timestamp > campaign.endAt, "Campaign not ended"
    assert not campaign.claimedByOwner, "Funds already claimed"
    assert (
        campaign.amountCollected >= campaign.goal
    ), "Campaign did not reach its goal"

    # 2. Effects
    self.s_campaigns[campaign_id].claimedByOwner = True

    # 3. Interaction
    extcall I_TOKEN.transfer(msg.sender, campaign.amountCollected)

    # 4. Events
    log CampaignAmountClaimed(
        campaignId=campaign_id,
        creator=msg.sender,
        amount=campaign.amountCollected,
    )


@external
@view
def getTotalCampaigns() -> uint256:
    """
    @notice Get the total number of campaigns created
    @return The total number of campaigns
    """
    return self.s_campaignsCount


@external
@view
def getCampaign(campaign_id: uint256) -> Campaign:
    """
    @notice Get the details of a specific campaign
    @param campaign_id The ID of the campaign to retrieve
    @return The campaign details
    """
    assert (
        campaign_id > 0 and campaign_id <= self.s_campaignsCount
    ), "Campaign does not exist"
    return self.s_campaigns[campaign_id]


@external
@view
def getAmountCollected(campaign_id: uint256) -> uint256:
    """
    @notice Get the amount collected for a specific campaign
    @param campaign_id The ID of the campaign
    @return The amount collected for the campaign
    """
    assert (
        campaign_id > 0 and campaign_id <= self.s_campaignsCount
    ), "Campaign does not exist"
    return self.s_campaigns[campaign_id].amountCollected


@external
@view
def getFundersOfCampaign(campaign_id: uint256) -> DynArray[address, 1000]:
    """
    @notice Get the list of funders for a specific campaign
    @param campaign_id The ID of the campaign
    @return The list of funders' addresses
    """
    assert (
        campaign_id > 0 and campaign_id <= self.s_campaignsCount
    ), "Campaign does not exist"
    return self.s_fundersOfCampaign[campaign_id]


@external
@view
def getCampaignsCreatedByCreator(creator: address) -> DynArray[Campaign, 1000]:
    """
    @notice Get the list of campaigns created by a specific creator
    @param creator The address of the creator
    @return The list of campaigns created by the creator
    """
    return self.s_campaignCreatedByCreator[creator]


@external
@view
def getAddressToAmountFundedByCampaign(
    campaign_id: uint256, funder: address
) -> uint256:
    """
    @notice Get the amount funded by a specific address for a specific campaign
    @param campaign_id The ID of the campaign
    @param funder The address of the funder
    @return The amount funded by the address for the campaign
    """
    assert (
        campaign_id > 0 and campaign_id <= self.s_campaignsCount
    ), "Campaign does not exist"
    return self.s_addressToAmountFundedByCampaign[campaign_id][funder]


@external
@view
def getAllCampaigns() -> DynArray[Campaign, 1000]:
    """
    @notice Get all campaigns
    @return The list of all campaigns
    """
    campaigns: DynArray[Campaign, 1000] = []
    count: uint256 = self.s_campaignsCount
    for i: uint256 in range(1, 1001):
        if i > count:
            break
        campaigns.append(self.s_campaigns[i])
    return campaigns
