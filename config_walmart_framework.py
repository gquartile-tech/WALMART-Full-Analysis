from __future__ import annotations

from dataclasses import dataclass

STATUS_OK      = "OK"
STATUS_PARTIAL = "PARTIAL"
STATUS_FLAG    = "FLAG"

PRIORITY_POINTS = {10: -18, 9: -15, 8: -13, 7: -11, 6: -9, 5: -7, 4: -5, 3: -3, 2: -2, 1: 0}
IMPACT_LABEL    = {10: 'Critical', 9: 'High', 8: 'High', 7: 'Medium', 6: 'Medium', 5: 'Medium', 4: 'Low', 3: 'Low', 2: 'Visibility', 1: 'Visibility'}

IMPORTANCE = {
    'WM-F001': 8,   # Sponsored Products Coverage
    'WM-F002': 6,   # Sponsored Brands / Video Coverage
    'WM-F003': 8,   # Sponsored Display Utilization
    'WM-F004': 8,   # SB Funded at Min 2%
    'WM-F005': 6,   # SPT Spend Share
    'WM-F006': 5,   # WATM Spend Share
    'WM-F007': 8,   # ATM Catalog Coverage Rate
    'WM-F008': 10,  # Brand (BA) Layer Exists
    'WM-F009': 8,   # Auto vs Manual Spend Ratio
    'WM-F010': 8,   # Sponsored Video ROAS Check
    'WM-F011': 7,   # Bidding Strategy Configured
    'WM-F012': 10,  # Advertised Item Coverage Rate
    'WM-F013': 6,   # New Item Onboarding Velocity
    'WM-F014': 8,   # Item Review Status Health
    'WM-F015': 9,   # Item Availability & Publish Status
    'WM-F016': 10,  # Zero-Inventory Items with Active Spend
}

CONTROL_NAMES = {
    'WM-F001': 'Sponsored Products Coverage',
    'WM-F002': 'Sponsored Brands / Video Coverage',
    'WM-F003': 'Sponsored Display (SD) Utilization',
    'WM-F004': 'SB Funded at Min 2% of Spend',
    'WM-F005': 'SPT Spend Share at Min 5%',
    'WM-F006': 'WATM Spend Share',
    'WM-F007': 'ATM Catalog Coverage Rate',
    'WM-F008': 'Brand (BA) Layer Exists',
    'WM-F009': 'Auto vs Manual Spend Ratio',
    'WM-F010': 'Sponsored Video (SV) ROAS Check',
    'WM-F011': 'Bidding Strategy Configured',
    'WM-F012': 'Advertised Item Coverage Rate',
    'WM-F013': 'New Item Onboarding Velocity',
    'WM-F014': 'Item Review Status Health',
    'WM-F015': 'Item Availability & Publish Status',
    'WM-F016': 'Zero-Inventory Items with Active Ad Spend',
}

WHY = {
    'WM-F001': 'SP is the primary Walmart search format. Its absence or zero spend signals a fundamental coverage gap that must be resolved before any other optimization.',
    'WM-F002': 'Upper-funnel awareness formats drive consideration and defend branded search share on Walmart. Accounts without SB or Video have no presence above the conversion layer.',
    'WM-F003': 'SD enables off-platform retargeting and audience targeting. Without SD, the funnel is not closed and retargeting audiences are not being captured.',
    'WM-F004': 'Under-investment in SB cedes branded search share to competitors and limits upper-funnel reach for accounts that have been live long enough to build audience data.',
    'WM-F005': 'SPT drives product page traffic and competitor conquest. Below 5% of spend signals a targeting gap that limits mid-funnel coverage.',
    'WM-F006': 'WATM campaigns are required for broad reach across Walmart search. Absence or very low share signals a coverage gap in the automatic targeting layer.',
    'WM-F007': 'ATM is the primary discovery mechanism on Walmart. Low ATM coverage leaves catalog items invisible to new-to-brand search traffic.',
    'WM-F008': 'Without a brand defense layer, competitors can capture branded search traffic at the bottom of the funnel. BA campaigns are non-negotiable for accounts with brand recognition.',
    'WM-F009': 'Over-reliance on auto targeting means bids are not being controlled at the keyword level. Efficiency degrades at scale when manual bid control is absent.',
    'WM-F010': 'SV spend without a minimum ROAS threshold signals creative or targeting misalignment. Video investment must be held to an efficiency floor.',
    'WM-F011': 'Undefined bidding strategy means Walmart is optimizing without direction. Every active campaign must have a bidding strategy assigned.',
    'WM-F012': 'Low item coverage means revenue-driving products are not being promoted. A direct gap in Walmart search presence results in missed sales.',
    'WM-F013': 'New catalog items not onboarded within 30 days means the account is not monetizing new inventory. Every item delayed is a missed revenue opportunity.',
    'WM-F014': 'Rejected or pending items do not serve and inflate the campaign roster with non-delivering ads. High rejection rates signal a systemic listing issue.',
    'WM-F015': 'Advertising out-of-stock or unpublished items wastes budget with zero conversion potential. These items must be excluded from active campaigns immediately.',
    'WM-F016': 'Running ads on zero-inventory items burns budget with no possible conversion. This is a direct and preventable waste that must be eliminated.',
}

SOURCES = {
    'WM-F001': '07_Campaigns_Grouped_by_Campaig',
    'WM-F002': '07_Campaigns_Grouped_by_Campaig',
    'WM-F003': '35_SD_Line_Item_Report',
    'WM-F004': '34_Campaign_Metadata + 06_Campaign_Report',
    'WM-F005': '34_Campaign_Metadata',
    'WM-F006': '34_Campaign_Metadata',
    'WM-F007': '34_Campaign_Metadata',
    'WM-F008': '12_Advertiser_Settings',
    'WM-F009': '28_Campaign_Placement_Settings',
    'WM-F010': '12_Advertiser_Settings',
    'WM-F011': '33_Ad_Item_Metadata',
    'WM-F012': '31_Ad_Group_Metadata',
    'WM-F013': '31_Ad_Group_Metadata',
    'WM-F014': '31_Ad_Group_Metadata + 33_Ad_Item_Metadata',
    'WM-F015': '26_Enhanced_Campaign_Details + 07_Campaigns_Grouped_by_Campaig',
    'WM-F016': '22_Product_Catalog + 33_Ad_Item_Metadata',
}


@dataclass(frozen=True)
class ControlResult:
    status: str
    what: str = ''
    why:  str = ''
    source: str = ''
