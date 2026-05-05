from __future__ import annotations

from dataclasses import dataclass

STATUS_OK      = "OK"
STATUS_PARTIAL = "PARTIAL"
STATUS_FLAG    = "FLAG"

PRIORITY_POINTS = {10: -30, 9: -27, 8: -24, 7: -21, 6: -18, 5: -15, 4: -10, 3: -5, 2: -2, 1: 0}
IMPACT_LABEL    = {10: 'Critical', 9: 'High', 8: 'High', 7: 'Medium', 6: 'Medium', 5: 'Medium', 4: 'Low', 3: 'Low', 2: 'Visibility', 1: 'Visibility'}

# Controls with Importance = 1 are Visibility-only — no scoring penalty applied.
VISIBILITY_ONLY = {
    'WM-H008', 'WM-H009', 'WM-H010', 'WM-H011',
    'WM-H014', 'WM-H015', 'WM-H016', 'WM-H017', 'WM-H018', 'WM-H019',
}

IMPORTANCE = {
    'WM-H001': 5,   # ACoS vs Project
    'WM-H002': 8,   # TACoS vs Project
    'WM-H003': 10,  # ROAS Trend
    'WM-H004': 10,  # Sales Trend
    'WM-H005': 10,  # Paid Dependency
    'WM-H006': 10,  # CTR Performance
    'WM-H007': 7,   # CVR Health
    'WM-H008': 1,   # CPC Trend (Visibility)
    'WM-H009': 1,   # YoY Trajectory (Visibility)
    'WM-H010': 1,   # High-Spend Zero-Order Keywords (Visibility)
    'WM-H011': 1,   # Match Type ACoS Floor (Visibility)
    'WM-H012': 1,   # Product Rating Health (Visibility)
    'WM-H013': 8,   # Product Review Floor
    'WM-H014': 1,   # Buybox Pricing (Visibility)
    'WM-H015': 1,   # Cancellation Rate (Visibility)
    'WM-H016': 1,   # 2-Day Shipping (Visibility)
    'WM-H017': 1,   # Refund Rate (Visibility)
    'WM-H018': 1,   # Product-Level ACoS Outliers (Visibility)
    'WM-H019': 1,   # Monthly Spend Trend (Visibility)
}

CONTROL_NAMES = {
    'WM-H001': 'ACoS vs Project',
    'WM-H002': 'TACoS vs Project',
    'WM-H003': 'ROAS Trend (L30 vs Prev30)',
    'WM-H004': 'Sales Trend',
    'WM-H005': 'Ad Sales vs Total Sales Ratio (Paid Dependency)',
    'WM-H006': 'CTR Performance',
    'WM-H007': 'CVR Health',
    'WM-H008': 'CPC Trend',
    'WM-H009': 'YoY Sales & Spend Trajectory',
    'WM-H010': 'High-Spend Zero-Order Keywords',
    'WM-H011': 'Match Type ACoS Floor',
    'WM-H012': 'Product Rating Health',
    'WM-H013': 'Product Review Floor',
    'WM-H014': 'Buybox Pricing Competitiveness',
    'WM-H015': 'Marketplace Order Cancellation Rate',
    'WM-H016': '2-Day Shipping Rate',
    'WM-H017': 'Refund Rate on Marketplace Orders',
    'WM-H018': 'Product-Level ACoS Outliers',
    'WM-H019': 'Monthly Spend Trend (L24M)',
}

WHY = {
    'WM-H001': 'ACoS above target signals bidding inefficiency or CVR degradation. Requires immediate diagnosis before any scaling decision.',
    'WM-H002': 'TACoS above target signals advertising is not generating organic lift. Every incremental dollar of spend is less productive than it should be.',
    'WM-H003': 'Declining ROAS is the earliest signal of structural efficiency loss. Catching it early avoids compounding spend waste.',
    'WM-H004': 'Sales decline without a strategic explanation requires immediate root cause investigation. Trend determines urgency.',
    'WM-H005': 'High paid dependency signals weak organic rank. The account is unsustainable at scale if more than 70% of sales require ad spend to generate.',
    'WM-H006': 'CTR decline on Walmart signals creative fatigue, relevance drop, or placement shift away from premium positions.',
    'WM-H007': 'CVR drop on Walmart is often tied to pricing uncompetitiveness, out-of-stock items, or review score degradation.',
    'WM-H008': 'CPC spikes signal increased auction competition or bid management issues. Visibility metric — no scoring penalty.',
    'WM-H009': 'YoY divergence between spend growth and sales growth reveals scaling efficiency loss or market share erosion. Visibility metric.',
    'WM-H010': 'Zero-conversion high-spend keywords are direct budget leakage. Visibility metric — review and negate manually.',
    'WM-H011': 'Any match type at ACoS over 100% is generating negative returns. Visibility metric for manual review.',
    'WM-H012': 'Low ratings suppress CVR regardless of ad efficiency. Advertising poor-rated items wastes every click. Visibility metric.',
    'WM-H013': 'Items with fewer than 10 reviews have insufficient social proof to convert. Ad spend on them is premature investment.',
    'WM-H014': 'Advertising an item that has lost the buy box wastes every click on Walmart. Visibility metric for manual review.',
    'WM-H015': 'High cancellation rate triggers Walmart algorithmic suppression of item ranking. Visibility metric — flag for ops review.',
    'WM-H016': 'Walmart rewards 2-day shipping with better organic placement. Low rates hurt both rank and CVR. Visibility metric.',
    'WM-H017': 'High refund rates signal product quality or fulfillment issues that suppress organic ranking over time. Visibility metric.',
    'WM-H018': 'Product-level ACoS outliers inflate account-level ACoS and mask structural issues in the catalog mix. Visibility metric.',
    'WM-H019': 'Declining spend trend without a strategic reason signals budget erosion or account disengagement. Visibility metric.',
}

SOURCES = {
    'WM-H001': '02_Date_Range_KPIs + 13_Product_Level_ACoS',
    'WM-H002': '02_Date_Range_KPIs + 14_Project_Dataset_on_SF',
    'WM-H003': '02_Date_Range_KPIs',
    'WM-H004': '02_Date_Range_KPIs',
    'WM-H005': '02_Date_Range_KPIs',
    'WM-H006': '02_Date_Range_KPIs',
    'WM-H007': '02_Date_Range_KPIs + 22_Product_Catalog',
    'WM-H008': '02_Date_Range_KPIs',
    'WM-H009': '03_Yearly_KPIs + 05_Monthly_Sales_YoY_Comparison',
    'WM-H010': '20_Keyword_Performance_Report',
    'WM-H011': '20_Keyword_Performance_Report',
    'WM-H012': '22_Product_Catalog',
    'WM-H013': '22_Product_Catalog',
    'WM-H014': '22_Product_Catalog',
    'WM-H015': '29_Marketplace_Order_Lines',
    'WM-H016': '29_Marketplace_Order_Lines',
    'WM-H017': '29_Marketplace_Order_Lines',
    'WM-H018': '13_Product_Level_ACoS',
    'WM-H019': '04_L24M_Monthly_Performance_Sum',
}


@dataclass(frozen=True)
class ControlResult:
    status: str
    what: str = ''
    why:  str = ''
    source: str = ''
