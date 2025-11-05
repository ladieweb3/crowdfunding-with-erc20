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

struct  Campaign:
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
        CampaignId: indexed(uint256)
        creator: indexed(address)
        goal: uint256
        startAt: uint256
        endAt: uint256

event CampaignFunded:
        CampaignId: indexed(uint256)
        funders: indexed(address)
        amount: uint256

event CampaignAmountClaimed:
        CampaignId: indexed(uint256)
        creator: indexed(address)
        amount: uint256


# ------------------------------------------------------------------
#                       IMMUTABLE VARIABLES
# ------------------------------------------------------------------

i_token: public(immutable(FundTokenInterface))


# ------------------------------------------------------------------
#                        STORAGE VARIABLES
# ------------------------------------------------------------------

# Compteur de campagnes
s_campaignsCount: uint256
# Mapping des campagnes par ID
s_campaigns: HashMap[uint256, Campaign]
# Mapping des financeurs par campagne (limité à 1000 financeurs)
s_fundersOfCampaign: public(HashMap[uint256, DynArray[address, 1000]])
# Mapping des campagnes créées par créateur (limité à 100 campagnes par créateur)
s_campaignCreatedByCreator: HashMap[address, DynArray[Campaign, 1000]]
# ReentrancyGuard
locked: bool
# Mapping du montant financé par adresse et par campagne
s_addressToAmountFundedByCampaign: HashMap[uint256, HashMap[address, uint256]]

# ------------------------------------------------------------------
#                           CONSTRUCTORS
# ------------------------------------------------------------------

@deploy
def __init__(_token: address): 
    i_token = FundTokenInterface(_token)
# ------------------------------------------------------------------
#                            FUNCTIONS
# ------------------------------------------------------------------


@internal
def non_reentrant():
    """
    @notice Modifier pour prévenir les appels réentrants
    """
    assert not self.locked, "Reentrant call"
    self.locked = True

@internal
def non_reentrant_final():
    """
    @notice Doit être appelé à la fin des fonctions protégées
    """
    self.locked = False

@external
def createCampaigns(
    name: String[25],
    description: String[100],
    goal: uint256,
    startAt: uint256,
    endAt: uint256,
    image: String[100]
) -> uint256:
    """
    @notice Create a new crowdfunding campaign
    @param name The name of the campaign
    @param description The description of the campaign
    @param goal The funding goal of the campaign
    @param startAt The start time of the campaign (timestamp)
    @param endAt The end time of the campaign (timestamp)
    @param image The image URL of the campaign
    @return The ID of the created campaign
    """
    assert startAt >= block.timestamp, "Start time must be in the future"
    assert endAt > startAt, "End time must be after start time"
    assert endAt <= block.timestamp + 90 * 86400, "End time must be within 90 days"

    self.s_campaignsCount += 1
    campaign_id: uint256 = self.s_campaignsCount

    # Créer la nouvelle campagne
    new_campaign: Campaign = Campaign(
        creator=msg.sender,
        name=name,
        description=description,
        goal=goal,
        amountCollected=0,
        startAt=startAt,
        endAt=endAt,
        image=image,
        funders=[],  # Liste vide simplifiée
        claimedByOwner=False
    )
    self.s_campaigns[campaign_id] = new_campaign

    self.s_campaignCreatedByCreator[msg.sender].append(new_campaign)

    log CampaignCreated(
    CampaignId=campaign_id,
    creator=msg.sender,
    goal=goal,
    startAt=startAt,
    endAt=endAt
    )

    return campaign_id

@external
def fundCampaign(campaign_id: uint256, amount: uint256):
    """
    @notice Fund a crowdfunding campaign
    @param campaign_id The ID of the campaign to fund
    @param amount The amount of funds to contribute
    """
    self.non_reentrant()

    assert amount > 0, "Amount must be greater than 0"
    campaign: Campaign = self.s_campaigns[campaign_id]
    assert block.timestamp >= campaign.startAt and block.timestamp <= campaign.endAt, "Campaign is not active"
    assert campaign_id > 0 and campaign_id <= self.s_campaignsCount, "Campaign does not exist"

    campaign.amountCollected += amount
    extcall i_token.approve(self, amount)
    extcall i_token.transferFrom(msg.sender, self, amount)
    self.s_addressToAmountFundedByCampaign[campaign_id][msg.sender] += amount
    self.s_fundersOfCampaign[campaign_id].append(msg.sender)
    self.non_reentrant_final()

    log CampaignFunded(
        CampaignId=campaign_id,
        funders=msg.sender,
        amount=amount
    )

@external
def claimAmount(campaign_id: uint256):
    """
    @notice Claim the collected funds for a successful campaign
    @param campaign_id The ID of the campaign to claim funds from
    """

    self.non_reentrant()

    campaign: Campaign = self.s_campaigns[campaign_id]
    assert campaign_id > 0 and campaign_id <= self.s_campaignsCount, "Campaign does not exist"
    assert campaign.creator == msg.sender, "Only the creator can claim funds"
    assert campaign.amountCollected >= campaign.goal, "Campaign did not reach its goal"
    assert not campaign.claimedByOwner, "Funds already claimed"

    campaign.claimedByOwner = True
    extcall i_token.transfer(msg.sender, campaign.amountCollected)

    self.non_reentrant_final()

    log CampaignAmountClaimed(
        CampaignId=campaign_id,
        creator=msg.sender,
        amount=campaign.amountCollected
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
    assert campaign_id > 0 and campaign_id <= self.s_campaignsCount, "Campaign does not exist"
    return self.s_campaigns[campaign_id]

@external
@view
def getFundersOfCampaign(campaign_id: uint256) -> DynArray[address, 1000]:
    """
    @notice Get the list of funders for a specific campaign
    @param campaign_id The ID of the campaign
    @return The list of funders' addresses
    """
    assert campaign_id > 0 and campaign_id <= self.s_campaignsCount, "Campaign does not exist"
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

