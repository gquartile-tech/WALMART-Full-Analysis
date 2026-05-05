from __future__ import annotations

import re
from datetime import date, datetime
from typing import Dict, Optional

import pandas as pd

from config_walmart_mastery import (
    CONTROL_NAMES, IMPACT_LABEL, IMPORTANCE, PRIORITY_POINTS,
    SOURCES, WHY, STATUS_FLAG, STATUS_OK, STATUS_PARTIAL, ControlResult,
)
from reader_databricks_walmart import WalmartContext, clean_text, norm_pct, pct_str, to_float, trim, _find_col

OBJECTIVE_WORDS = {
    'objective', 'goal', 'grow', 'growth', 'scale', 'increase', 'improve',
    'stabilize', 'maintain', 'reduce', 'defend', 'accelerate', 'awareness',
    'sales', 'profit', 'profitability', 'ranking', 'market share',
}
CHALLENGE_WORDS = {
    'challenge', 'issue', 'risk', 'inventory', 'out-of-stock', 'out of stock',
    'slowdown', 'pressure', 'volatility', 'buy box', 'listing', 'margin',
    'competition', 'competitive', 'not meeting', 'dissatisfied',
}
SEASON_WORDS = {
    'q1', 'q2', 'q3', 'q4', 'seasonal', 'seasonality', 'peak', 'holiday',
    'black friday', 'cyber monday', 'prime day', 'back to school',
}


def _has_any(text: str, words: set) -> bool:
    t = clean_text(text).lower()
    return any(w in t for w in words)


def _nonempty(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None
    tmp = df.dropna(how='all')
    return tmp if not tmp.empty else None


def evaluate_all(ctx: WalmartContext) -> Dict[str, ControlResult]:
    r: Dict[str, ControlResult] = {}

    # ── WM-M001: Account Objectives Defined ──────────────────────────────────
    obj = clean_text(ctx.cs_objective)
    if obj and len(obj) >= 20 and _has_any(obj, OBJECTIVE_WORDS):
        r['WM-M001'] = ControlResult(
            STATUS_OK,
            f'Objective documented: "{trim(obj, 120)}"',
            WHY['WM-M001'], SOURCES['WM-M001'],
        )
    elif obj and len(obj) >= 10:
        r['WM-M001'] = ControlResult(
            STATUS_PARTIAL,
            f'An objective is documented but lacks specificity: "{trim(obj, 120)}"',
            WHY['WM-M001'], SOURCES['WM-M001'],
        )
    else:
        r['WM-M001'] = ControlResult(
            STATUS_FLAG,
            'No advertising objective is documented in the Client Success Insights Report.',
            WHY['WM-M001'], SOURCES['WM-M001'],
        )

    # ── WM-M002: SF Target Completeness (3 targets) ───────────────────────────
    has_acos  = ctx.proj_acos_target  is not None
    has_roas  = ctx.proj_roas_target  is not None
    has_tacos = ctx.proj_tacos_target is not None
    n_set = sum([has_acos, has_roas, has_tacos])

    acos_s  = pct_str(ctx.proj_acos_target)  if has_acos  else 'missing'
    roas_s  = f'{ctx.proj_roas_target:.2f}x' if has_roas  else 'missing'
    tacos_s = pct_str(ctx.proj_tacos_target) if has_tacos else 'missing'
    detail  = f'ACoS target: {acos_s} | ROAS target: {roas_s} | TACoS target: {tacos_s}'

    if n_set == 3:
        r['WM-M002'] = ControlResult(STATUS_OK, f'All 3 targets documented. {detail}', WHY['WM-M002'], SOURCES['WM-M002'])
    elif n_set >= 1:
        r['WM-M002'] = ControlResult(STATUS_PARTIAL, f'{n_set} of 3 targets documented. {detail}', WHY['WM-M002'], SOURCES['WM-M002'])
    else:
        r['WM-M002'] = ControlResult(STATUS_FLAG, f'No KPI targets documented in project dataset. {detail}', WHY['WM-M002'], SOURCES['WM-M002'])

    # ── WM-M003: Objective vs Near-Term Alignment ─────────────────────────────
    obj_text  = clean_text(ctx.cs_objective)
    proj_text = clean_text(ctx.proj_notes)
    combined  = f'{obj_text} {proj_text}'.lower()
    has_kpi   = any(k in combined for k in ['acos', 'roas', 'tacos', 'spend', 'sales'])
    has_time  = any(k in combined for k in ['q1', 'q2', 'q3', 'q4', 'month', 'period', 'near-term'])

    if obj_text and has_kpi and has_time and n_set >= 2:
        r['WM-M003'] = ControlResult(STATUS_OK, 'Objective, KPI targets, and timeframe context are all present and aligned.', WHY['WM-M003'], SOURCES['WM-M003'])
    elif obj_text and has_kpi:
        r['WM-M003'] = ControlResult(STATUS_PARTIAL, 'Objective and KPI context are present but timeframe or target alignment is incomplete.', WHY['WM-M003'], SOURCES['WM-M003'])
    else:
        r['WM-M003'] = ControlResult(STATUS_FLAG, 'Objective narrative and KPI target alignment are not documented together. Cannot assess near-term alignment.', WHY['WM-M003'], SOURCES['WM-M003'])

    # ── WM-M004: Account Challenges Documented ────────────────────────────────
    chal = clean_text(ctx.cs_challenges)
    if chal and len(chal) >= 20 and _has_any(chal, CHALLENGE_WORDS):
        r['WM-M004'] = ControlResult(STATUS_OK, f'Challenges documented: "{trim(chal, 120)}"', WHY['WM-M004'], SOURCES['WM-M004'])
    elif chal and len(chal) >= 10:
        r['WM-M004'] = ControlResult(STATUS_PARTIAL, f'A challenge note exists but lacks specificity: "{trim(chal, 80)}"', WHY['WM-M004'], SOURCES['WM-M004'])
    else:
        r['WM-M004'] = ControlResult(STATUS_FLAG, 'No account challenges are documented in the Client Success Insights Report.', WHY['WM-M004'], SOURCES['WM-M004'])

    # ── WM-M005: Seasonality Awareness ───────────────────────────────────────
    seas = clean_text(ctx.cs_seasonality)
    if seas and _has_any(seas, SEASON_WORDS):
        r['WM-M005'] = ControlResult(STATUS_OK, f'Seasonality documented: "{trim(seas, 120)}"', WHY['WM-M005'], SOURCES['WM-M005'])
    elif seas and len(seas) >= 10:
        r['WM-M005'] = ControlResult(STATUS_PARTIAL, f'Seasonality note exists but no specific season or period identified: "{trim(seas, 80)}"', WHY['WM-M005'], SOURCES['WM-M005'])
    else:
        r['WM-M005'] = ControlResult(STATUS_OK, 'No seasonality documented — treated as non-seasonal account.', WHY['WM-M005'], SOURCES['WM-M005'])

    # ── WM-M006: Client Contact Cadence ──────────────────────────────────────
    gap = ctx.gong_gap_days
    last = ctx.gong_last_call

    if last is None:
        r['WM-M006'] = ControlResult(STATUS_FLAG, 'No Gong call records found. Cannot assess client contact cadence.', WHY['WM-M006'], SOURCES['WM-M006'])
    else:
        last_str = last.strftime('%Y-%m-%d') if hasattr(last, 'strftime') else str(last)
        if gap is None:
            r['WM-M006'] = ControlResult(STATUS_PARTIAL, f'Only one call record found. Last call: {last_str}. Cannot compute cadence gap.', WHY['WM-M006'], SOURCES['WM-M006'])
        elif gap <= 45:
            r['WM-M006'] = ControlResult(STATUS_OK, f'Last call: {last_str} — {gap} days since previous call. Cadence is within acceptable range.', WHY['WM-M006'], SOURCES['WM-M006'])
        elif gap <= 90:
            r['WM-M006'] = ControlResult(STATUS_PARTIAL, f'Last call: {last_str} — {gap} days since previous call. Cadence is wider than recommended (45 days).', WHY['WM-M006'], SOURCES['WM-M006'])
        else:
            r['WM-M006'] = ControlResult(STATUS_FLAG, f'Last call: {last_str} — {gap} days since previous call. Client contact cadence is critically overdue (>90 days).', WHY['WM-M006'], SOURCES['WM-M006'])

    # ── WM-M007: Client Journey Stage Mapped ─────────────────────────────────
    stage = clean_text(ctx.journey_stage)
    if stage and len(stage) >= 3:
        r['WM-M007'] = ControlResult(STATUS_OK, f'Client journey stage documented as: "{stage}"', WHY['WM-M007'], SOURCES['WM-M007'])
    else:
        r['WM-M007'] = ControlResult(STATUS_FLAG, 'Client journey stage is not documented in the Journey Insights Data.', WHY['WM-M007'], SOURCES['WM-M007'])

    # ── WM-M008: Narrative Consistency ───────────────────────────────────────
    proj_acos  = ctx.proj_acos_target
    proj_tacos = ctx.proj_tacos_target
    cs_text    = clean_text(ctx.cs_objective)

    acos_in_cs  = 'acos'  in cs_text.lower()
    tacos_in_cs = 'tacos' in cs_text.lower()

    if proj_acos is not None and proj_tacos is not None and (acos_in_cs or tacos_in_cs):
        r['WM-M008'] = ControlResult(STATUS_OK, 'KPI targets in the project dataset are consistent with the objective narrative in CS notes.', WHY['WM-M008'], SOURCES['WM-M008'])
    elif proj_acos is not None or proj_tacos is not None:
        r['WM-M008'] = ControlResult(STATUS_PARTIAL, 'KPI targets are partially documented but the CS objective narrative does not reference them explicitly. Consistency cannot be confirmed.', WHY['WM-M008'], SOURCES['WM-M008'])
    else:
        r['WM-M008'] = ControlResult(STATUS_FLAG, 'Neither the project dataset targets nor the CS objective narrative are sufficiently populated to assess narrative consistency.', WHY['WM-M008'], SOURCES['WM-M008'])

    # ── WM-M009: Customizations Documented & Justified ───────────────────────
    custom = clean_text(ctx.cs_customizations)
    if custom and len(custom) >= 20:
        r['WM-M009'] = ControlResult(STATUS_OK, f'Customizations documented: "{trim(custom, 120)}"', WHY['WM-M009'], SOURCES['WM-M009'])
    elif custom and len(custom) >= 5:
        r['WM-M009'] = ControlResult(STATUS_PARTIAL, f'A customization note exists but lacks detail: "{trim(custom, 80)}"', WHY['WM-M009'], SOURCES['WM-M009'])
    else:
        r['WM-M009'] = ControlResult(STATUS_OK, 'No customizations documented — treated as standard setup.', WHY['WM-M009'], SOURCES['WM-M009'])

    # ── WM-M010: Quartile Management Rate ────────────────────────────────────
    df_meta = _nonempty(ctx.df_campaign_meta)
    if df_meta is None:
        r['WM-M010'] = ControlResult(STATUS_FLAG, 'Campaign metadata not available. Cannot compute Quartile management rate.', WHY['WM-M010'], SOURCES['WM-M010'])
    else:
        status_col = _find_col(df_meta, 'CampaignStatus', 'Status', 'status')
        qt_col     = _find_col(df_meta, 'IsQuartile', 'isquartile', 'Quartile')

        active = df_meta
        if status_col:
            active = df_meta[df_meta[status_col].astype(str).str.upper().str.strip() == 'ACTIVE']

        total_active = len(active)
        if total_active == 0:
            r['WM-M010'] = ControlResult(STATUS_FLAG, 'No active campaigns found in campaign metadata.', WHY['WM-M010'], SOURCES['WM-M010'])
        elif qt_col is None:
            r['WM-M010'] = ControlResult(STATUS_PARTIAL, f'{total_active} active campaigns found but IsQuartile column is missing. Cannot verify QT management rate.', WHY['WM-M010'], SOURCES['WM-M010'])
        else:
            qt_vals = active[qt_col].astype(str).str.strip().str.upper()
            qt_managed = (qt_vals.isin(['TRUE', '1', 'YES'])).sum()
            rate = qt_managed / total_active if total_active > 0 else 0.0
            rate_pct = f'{rate * 100:.1f}%'

            if rate >= 0.90:
                r['WM-M010'] = ControlResult(STATUS_OK, f'{qt_managed} of {total_active} active campaigns managed by Quartile ({rate_pct}). Management rate is above 90% threshold.', WHY['WM-M010'], SOURCES['WM-M010'])
            elif rate >= 0.70:
                r['WM-M010'] = ControlResult(STATUS_PARTIAL, f'{qt_managed} of {total_active} active campaigns managed by Quartile ({rate_pct}). Below 90% target — manual gaps detected.', WHY['WM-M010'], SOURCES['WM-M010'])
            else:
                r['WM-M010'] = ControlResult(STATUS_FLAG, f'Only {qt_managed} of {total_active} active campaigns managed by Quartile ({rate_pct}). Significantly below 90% target.', WHY['WM-M010'], SOURCES['WM-M010'])

    # ── WM-M011: QT Campaign Type Tagging ────────────────────────────────────
    df_meta = _nonempty(ctx.df_campaign_meta)
    if df_meta is None:
        r['WM-M011'] = ControlResult(STATUS_FLAG, 'Campaign metadata not available. Cannot verify QT campaign type tagging.', WHY['WM-M011'], SOURCES['WM-M011'])
    else:
        qt_col   = _find_col(df_meta, 'IsQuartile', 'isquartile', 'Quartile')
        type_col = _find_col(df_meta, 'QuartileCampaignType', 'QT_CampaignType', 'CampaignType')

        if qt_col is None:
            r['WM-M011'] = ControlResult(STATUS_PARTIAL, 'IsQuartile column not found. Cannot verify QT campaign type tagging.', WHY['WM-M011'], SOURCES['WM-M011'])
        elif type_col is None:
            r['WM-M011'] = ControlResult(STATUS_FLAG, 'QuartileCampaignType column not found. QT campaigns cannot be verified as correctly tagged.', WHY['WM-M011'], SOURCES['WM-M011'])
        else:
            qt_mask = df_meta[qt_col].astype(str).str.strip().str.upper().isin(['TRUE', '1', 'YES'])
            qt_campaigns = df_meta[qt_mask]
            total_qt = len(qt_campaigns)

            if total_qt == 0:
                r['WM-M011'] = ControlResult(STATUS_FLAG, 'No Quartile campaigns found. Cannot verify QT campaign type tagging.', WHY['WM-M011'], SOURCES['WM-M011'])
            else:
                untagged = qt_campaigns[qt_campaigns[type_col].isna() | (qt_campaigns[type_col].astype(str).str.strip() == '')].shape[0]
                if untagged == 0:
                    r['WM-M011'] = ControlResult(STATUS_OK, f'All {total_qt} Quartile campaigns have a QuartileCampaignType assigned.', WHY['WM-M011'], SOURCES['WM-M011'])
                elif untagged / total_qt <= 0.10:
                    r['WM-M011'] = ControlResult(STATUS_PARTIAL, f'{untagged} of {total_qt} Quartile campaigns are missing QuartileCampaignType ({untagged/total_qt*100:.1f}%). Minor tagging gap.', WHY['WM-M011'], SOURCES['WM-M011'])
                else:
                    r['WM-M011'] = ControlResult(STATUS_FLAG, f'{untagged} of {total_qt} Quartile campaigns are missing QuartileCampaignType ({untagged/total_qt*100:.1f}%). Automation attribution is broken for these campaigns.', WHY['WM-M011'], SOURCES['WM-M011'])

    return r


def compute_score(results: Dict[str, ControlResult]):
    findings = []
    total_penalty = 0.0

    for cid, res in results.items():
        imp = IMPORTANCE[cid]
        pen = 0.0
        if res.status == STATUS_FLAG:
            pen = PRIORITY_POINTS[imp]
        elif res.status == STATUS_PARTIAL:
            pen = PRIORITY_POINTS[imp] * 0.5
        total_penalty += pen
        findings.append({
            'cid': cid,
            'name': CONTROL_NAMES[cid],
            'status': res.status,
            'what': res.what,
            'why': res.why,
            'importance': imp,
            'impact': IMPACT_LABEL[imp],
            'penalty': pen,
        })

    score = 100 + total_penalty
    grade = 'Compliant' if score >= 75 else ('Needs Attention' if score >= 40 else 'Not Compliant')
    findings.sort(key=lambda x: (0 if x['status'] == STATUS_FLAG else 1 if x['status'] == STATUS_PARTIAL else 2, x['penalty']))
    return total_penalty, score, grade, findings


def interpretation(grade: str) -> str:
    return {
        'Compliant': 'Account mastery signals are documented and internally consistent. Documentation and client communication are sufficient to support strategic decision-making.',
        'Needs Attention': 'Some mastery elements are present but important documentation or consistency gaps need follow-up before the account review can be considered complete.',
        'Not Compliant': 'Key mastery signals are missing or inconsistent. This limits confidence in account ownership and the accuracy of the account narrative.',
    }.get(grade, '')
