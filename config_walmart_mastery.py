from __future__ import annotations

from dataclasses import dataclass

STATUS_OK      = "OK"
STATUS_PARTIAL = "PARTIAL"
STATUS_FLAG    = "FLAG"

PRIORITY_POINTS = {10: -18, 9: -15, 8: -13, 7: -11, 6: -9, 5: -7, 4: -5, 3: -3, 2: -2, 1: 0}
IMPACT_LABEL    = {10: 'Critical', 9: 'High', 8: 'High', 7: 'Medium', 6: 'Medium', 5: 'Medium', 4: 'Low', 3: 'Low', 2: 'Visibility', 1: 'Visibility'}

IMPORTANCE = {
    'WM-M001': 10,  # Account Objectives Defined
    'WM-M002': 8,   # SF Target Completeness
    'WM-M003': 9,   # Objective vs Near-Term Alignment
    'WM-M004': 6,   # Account Challenges Documented
    'WM-M005': 8,   # Seasonality Awareness
    'WM-M006': 8,   # Client Contact Cadence
    'WM-M007': 9,   # Client Journey Stage Mapped
    'WM-M008': 6,   # Narrative Consistency
    'WM-M009': 5,   # Customizations Documented
    'WM-M010': 9,   # Quartile Management Rate
    'WM-M011': 10,  # QT Campaign Type Tagging
}

CONTROL_NAMES = {
    'WM-M001': 'Account Objectives Defined',
    'WM-M002': 'SF Target Completeness (3 targets)',
    'WM-M003': 'Objective vs Near-Term Alignment',
    'WM-M004': 'Account Challenges Documented',
    'WM-M005': 'Seasonality Awareness',
    'WM-M006': 'Client Contact Cadence',
    'WM-M007': 'Client Journey Stage Mapped',
    'WM-M008': 'Narrative Consistency Across Documents',
    'WM-M009': 'Customizations Documented & Justified',
    'WM-M010': 'Quartile Management Rate',
    'WM-M011': 'QT Campaign Type Tagging',
}

WHY = {
    'WM-M001': 'A clear objective is the starting point for every strategy decision. Without it, the team cannot prioritize correctly or explain trade-offs to the client.',
    'WM-M002': 'Without ACoS, ROAS, and TACoS targets all documented, performance cannot be evaluated against intent. Partial targets create blind spots in account reviews.',
    'WM-M003': 'The objective context needs KPI targets and a timeframe. Misalignment between the declared objective and live strategy means budget is optimized for the wrong outcome.',
    'WM-M004': 'Knowing the active challenges helps the team avoid repeating mistakes and explains why certain metrics are moving. Generic descriptions do not help the reviewer.',
    'WM-M005': 'Seasonal accounts need a documented plan. If seasonality is not captured, the team may invest too much or too little at the wrong time.',
    'WM-M006': 'Regular client contact keeps the account story current. A long gap between calls means the documented goals may no longer reflect what the client actually wants.',
    'WM-M007': 'Journey stage drives recommended strategy — onboarding, growth, and mature accounts need different approaches. Without it, strategy decisions may not match the client stage.',
    'WM-M008': 'The efficiency targets set in the project must respect the limits agreed with the client. Inconsistent targets across documents signal misalignment between CSM intent and documented strategy.',
    'WM-M009': 'Framework exceptions must be documented so the CoE can tell if they are intentional. Undocumented customizations look like errors during a review.',
    'WM-M010': 'Low Quartile management rate means the platform automation engine is not covering the full account. Manual gaps create inconsistency and degrade optimization quality.',
    'WM-M011': 'Untagged Quartile campaigns break automation logic and make performance attribution impossible. Every active QT campaign must have a QuartileCampaignType assigned.',
}

SOURCES = {
    'WM-M001': '17_Client_Success_Insights_Repo',
    'WM-M002': '14_Project_Dataset_on_SF',
    'WM-M003': '17_Client_Success_Insights_Repo + 14_Project_Dataset_on_SF',
    'WM-M004': '17_Client_Success_Insights_Repo',
    'WM-M005': '17_Client_Success_Insights_Repo + 04_L24M_Monthly_Performance_Sum',
    'WM-M006': '15_Gong_Call_Insights',
    'WM-M007': '18_Client_Journey_Insights_Data',
    'WM-M008': '14_Project_Dataset_on_SF + 17_Client_Success_Insights_Repo',
    'WM-M009': '17_Client_Success_Insights_Repo + 14_Project_Dataset_on_SF',
    'WM-M010': '34_Campaign_Metadata',
    'WM-M011': '34_Campaign_Metadata',
}


@dataclass(frozen=True)
class ControlResult:
    status: str
    what: str = ''
    why:  str = ''
    source: str = ''
