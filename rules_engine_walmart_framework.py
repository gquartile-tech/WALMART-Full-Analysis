from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from config_walmart_framework import (
    CONTROL_NAMES, IMPACT_LABEL, IMPORTANCE, PRIORITY_POINTS,
    SOURCES, WHY, STATUS_FLAG, STATUS_OK, STATUS_PARTIAL, ControlResult,
)
from reader_databricks_walmart import WalmartContext, clean_text, pct_str, to_float, _find_col

SP_TYPES    = {'sponsoredproducts', 'sp', 'sponsored_products'}
SB_TYPES    = {'sponsoredbrands', 'sb', 'sponsored_brands', 'video', 'sbvideo', 'sb_video'}
SD_TYPES    = {'sponsoreddisplay', 'sd', 'sponsored_display'}
SV_TYPES    = {'sponsoredvideo', 'sv', 'sponsored_video', 'video'}
ATM_TYPES   = {'atm', 'auto', 'automatic', 'automatictargetingmatch'}
BA_TYPES    = {'ba', 'brand', 'brandawareness', 'brand_awareness', 'branded'}
SPT_TYPES   = {'spt', 'sponsoredproducttargeting', 'product_targeting'}
WATM_TYPES  = {'watm', 'walmart_atm', 'walmartatm'}


def _nonempty(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None
    tmp = df.dropna(how='all')
    return tmp if not tmp.empty else None


def _type_matches(val: str, types: set) -> bool:
    v = clean_text(val).lower().replace(' ', '').replace('_', '')
    return v in types or any(t in v for t in types)


def _get_spend(df: pd.DataFrame) -> Optional[float]:
    col = _find_col(df, 'Spend', 'AdSpend', 'Ad_Spend', 'TotalSpend')
    if col is None:
        return None
    return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()


def _get_sales(df: pd.DataFrame) -> Optional[float]:
    col = _find_col(df, 'Sales', 'AdSales', 'Ad_Sales')
    if col is None:
        return None
    return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()


def evaluate_all(ctx: WalmartContext) -> Dict[str, ControlResult]:
    r: Dict[str, ControlResult] = {}

    grp = _nonempty(ctx.df_campaigns_grouped)
    meta = _nonempty(ctx.df_campaign_meta)
    ad_items = _nonempty(ctx.df_ad_items)
    catalog = _nonempty(ctx.df_product_catalog)
    ad_groups = _nonempty(ctx.df_ad_groups)
    qt_camps = _nonempty(ctx.df_qt_campaigns)
    advertiser = _nonempty(ctx.df_advertiser)

    # ── WM-F001: Sponsored Products Coverage ─────────────────────────────────
    if grp is None:
        r['WM-F001'] = ControlResult(STATUS_FLAG, 'Campaign group data not available. Cannot verify SP coverage.', WHY['WM-F001'], SOURCES['WM-F001'])
    else:
        type_col  = _find_col(grp, 'CampaignType', 'Campaign_Type', 'Type')
        spend_col = _find_col(grp, 'Spend', 'AdSpend', 'TotalSpend')

        if type_col is None:
            r['WM-F001'] = ControlResult(STATUS_PARTIAL, 'CampaignType column not found in campaigns grouped data.', WHY['WM-F001'], SOURCES['WM-F001'])
        else:
            sp_rows  = grp[grp[type_col].astype(str).str.lower().str.replace(' ', '').str.replace('_', '').isin(SP_TYPES)]
            sp_spend = pd.to_numeric(sp_rows[spend_col], errors='coerce').fillna(0).sum() if spend_col else 0.0
            sp_pct   = sp_spend / _get_spend(grp) * 100 if _get_spend(grp) else 0.0

            if sp_spend > 0 and sp_pct >= 50:
                r['WM-F001'] = ControlResult(STATUS_OK, f'SP campaigns are active with ${sp_spend:,.0f} spend ({sp_pct:.1f}% of total). Coverage is within expected range.', WHY['WM-F001'], SOURCES['WM-F001'])
            elif sp_spend > 0:
                r['WM-F001'] = ControlResult(STATUS_PARTIAL, f'SP campaigns have spend (${sp_spend:,.0f}, {sp_pct:.1f}% of total) but are below the 50% minimum expected share.', WHY['WM-F001'], SOURCES['WM-F001'])
            else:
                r['WM-F001'] = ControlResult(STATUS_FLAG, 'No SP campaign spend detected. Sponsored Products is the primary Walmart search format — this is a critical coverage gap.', WHY['WM-F001'], SOURCES['WM-F001'])

    # ── WM-F002: Sponsored Brands / Video Coverage ────────────────────────────
    if grp is None:
        r['WM-F002'] = ControlResult(STATUS_FLAG, 'Campaign group data not available.', WHY['WM-F002'], SOURCES['WM-F002'])
    else:
        type_col  = _find_col(grp, 'CampaignType', 'Campaign_Type', 'Type')
        spend_col = _find_col(grp, 'Spend', 'AdSpend', 'TotalSpend')
        total_spend = _get_spend(grp) or 0.0

        if type_col is None:
            r['WM-F002'] = ControlResult(STATUS_PARTIAL, 'CampaignType column not found. Cannot verify SB/Video coverage.', WHY['WM-F002'], SOURCES['WM-F002'])
        else:
            sb_rows  = grp[grp[type_col].astype(str).apply(lambda v: _type_matches(v, SB_TYPES))]
            sb_spend = pd.to_numeric(sb_rows[spend_col], errors='coerce').fillna(0).sum() if spend_col else 0.0
            sb_pct   = sb_spend / total_spend * 100 if total_spend > 0 else 0.0

            if sb_spend > 0 and sb_pct >= 2:
                r['WM-F002'] = ControlResult(STATUS_OK, f'SB/Video campaigns active with ${sb_spend:,.0f} spend ({sb_pct:.1f}% of total).', WHY['WM-F002'], SOURCES['WM-F002'])
            elif sb_spend > 0:
                r['WM-F002'] = ControlResult(STATUS_PARTIAL, f'SB/Video present but underfunded: ${sb_spend:,.0f} ({sb_pct:.1f}% of total). Minimum 2% expected.', WHY['WM-F002'], SOURCES['WM-F002'])
            else:
                r['WM-F002'] = ControlResult(STATUS_FLAG, 'No SB or Video campaign spend detected. Upper-funnel coverage is absent.', WHY['WM-F002'], SOURCES['WM-F002'])

    # ── WM-F003: Sponsored Display Utilization ────────────────────────────────
    sd = _nonempty(ctx.df_sd_line_items)
    if sd is not None and len(sd) > 0:
        r['WM-F003'] = ControlResult(STATUS_OK, f'{len(sd)} SD line item(s) found. Display coverage is active.', WHY['WM-F003'], SOURCES['WM-F003'])
    elif grp is not None:
        type_col = _find_col(grp, 'CampaignType', 'Campaign_Type', 'Type')
        if type_col:
            sd_rows = grp[grp[type_col].astype(str).apply(lambda v: _type_matches(v, SD_TYPES))]
            if len(sd_rows) > 0:
                r['WM-F003'] = ControlResult(STATUS_PARTIAL, 'SD campaign type found in grouped data but no SD line items detected. Verify SD configuration.', WHY['WM-F003'], SOURCES['WM-F003'])
            else:
                r['WM-F003'] = ControlResult(STATUS_FLAG, 'No Sponsored Display line items or SD campaigns detected. Off-platform retargeting is not active.', WHY['WM-F003'], SOURCES['WM-F003'])
        else:
            r['WM-F003'] = ControlResult(STATUS_FLAG, 'Sponsored Display data not available. Cannot verify SD utilization.', WHY['WM-F003'], SOURCES['WM-F003'])
    else:
        r['WM-F003'] = ControlResult(STATUS_FLAG, 'No SD data found. Off-platform retargeting is not active.', WHY['WM-F003'], SOURCES['WM-F003'])

    # ── WM-F004: SB Funded at Min 2% ─────────────────────────────────────────
    if grp is None:
        r['WM-F004'] = ControlResult(STATUS_FLAG, 'Campaign data not available.', WHY['WM-F004'], SOURCES['WM-F004'])
    else:
        type_col    = _find_col(grp, 'CampaignType', 'Campaign_Type', 'Type')
        spend_col   = _find_col(grp, 'Spend', 'AdSpend')
        total_spend = _get_spend(grp) or 0.0

        if type_col and spend_col and total_spend > 0:
            sb_rows  = grp[grp[type_col].astype(str).apply(lambda v: _type_matches(v, SB_TYPES))]
            sb_spend = pd.to_numeric(sb_rows[spend_col], errors='coerce').fillna(0).sum()
            sb_pct   = sb_spend / total_spend

            if sb_pct >= 0.02:
                r['WM-F004'] = ControlResult(STATUS_OK, f'SB funded at {sb_pct*100:.1f}% of total spend (${sb_spend:,.0f}). Meets 2% minimum threshold.', WHY['WM-F004'], SOURCES['WM-F004'])
            elif sb_pct > 0:
                r['WM-F004'] = ControlResult(STATUS_PARTIAL, f'SB funded at {sb_pct*100:.1f}% of total spend — below 2% minimum. Increase SB investment for accounts live >6 months.', WHY['WM-F004'], SOURCES['WM-F004'])
            else:
                r['WM-F004'] = ControlResult(STATUS_FLAG, 'SB spend is zero. Brand awareness layer is not funded.', WHY['WM-F004'], SOURCES['WM-F004'])
        else:
            r['WM-F004'] = ControlResult(STATUS_PARTIAL, 'Cannot compute SB share — spend or type columns missing.', WHY['WM-F004'], SOURCES['WM-F004'])

    # ── WM-F005: SPT Spend Share ──────────────────────────────────────────────
    def _qt_spend_share(qt_type_vals: set, label: str, threshold: float, ctrl_id: str):
        if qt_camps is None:
            return ControlResult(STATUS_PARTIAL, f'{label} data not available in QT campaigns tab.', WHY[ctrl_id], SOURCES[ctrl_id])
        type_col  = _find_col(qt_camps, 'QuartileCampaignType', 'QT_Type', 'CampaignType')
        spend_col = _find_col(qt_camps, 'Spend', 'AdSpend')
        if type_col is None or spend_col is None:
            return ControlResult(STATUS_PARTIAL, f'Required columns missing in QT campaigns. Cannot verify {label} spend share.', WHY[ctrl_id], SOURCES[ctrl_id])
        total = pd.to_numeric(qt_camps[spend_col], errors='coerce').fillna(0).sum()
        matched = qt_camps[qt_camps[type_col].astype(str).apply(lambda v: _type_matches(v, qt_type_vals))]
        matched_spend = pd.to_numeric(matched[spend_col], errors='coerce').fillna(0).sum()
        pct = matched_spend / total if total > 0 else 0.0

        if pct >= threshold:
            return ControlResult(STATUS_OK, f'{label} campaigns account for {pct*100:.1f}% of QT spend (${matched_spend:,.0f}). Meets {threshold*100:.0f}% threshold.', WHY[ctrl_id], SOURCES[ctrl_id])
        elif pct > 0:
            return ControlResult(STATUS_PARTIAL, f'{label} at {pct*100:.1f}% of QT spend — below {threshold*100:.0f}% minimum threshold.', WHY[ctrl_id], SOURCES[ctrl_id])
        else:
            return ControlResult(STATUS_FLAG, f'No {label} spend detected. Targeting coverage gap identified.', WHY[ctrl_id], SOURCES[ctrl_id])

    r['WM-F005'] = _qt_spend_share(SPT_TYPES,  'SPT',  0.05, 'WM-F005')
    r['WM-F006'] = _qt_spend_share(WATM_TYPES, 'WATM', 0.03, 'WM-F006')

    # ── WM-F007: ATM Catalog Coverage Rate ───────────────────────────────────
    if catalog is None or ad_items is None:
        r['WM-F007'] = ControlResult(STATUS_PARTIAL, 'Product catalog or ad item data not available. Cannot compute ATM coverage.', WHY['WM-F007'], SOURCES['WM-F007'])
    else:
        cat_id_col  = _find_col(catalog, 'ItemId', 'Item_Id', 'ITEM_ID', 'ProductId')
        item_id_col = _find_col(ad_items, 'ItemId', 'Item_Id', 'ITEM_ID')
        type_col    = _find_col(ad_items, 'QuartileCampaignType', 'CampaignType', 'Type')

        if cat_id_col is None or item_id_col is None:
            r['WM-F007'] = ControlResult(STATUS_PARTIAL, 'ItemId columns missing. Cannot compute ATM coverage rate.', WHY['WM-F007'], SOURCES['WM-F007'])
        else:
            total_items = catalog[cat_id_col].dropna().nunique()
            if type_col:
                atm_items_df = ad_items[ad_items[type_col].astype(str).apply(lambda v: _type_matches(v, ATM_TYPES))]
                atm_item_ids = atm_items_df[item_id_col].dropna().unique()
            else:
                atm_item_ids = ad_items[item_id_col].dropna().unique()

            n_covered = len(set(atm_item_ids))
            rate = n_covered / total_items if total_items > 0 else 0.0

            if rate >= 0.85:
                r['WM-F007'] = ControlResult(STATUS_OK, f'ATM covers {n_covered} of {total_items} catalog items ({rate*100:.1f}%). Meets 85% threshold.', WHY['WM-F007'], SOURCES['WM-F007'])
            elif rate >= 0.60:
                r['WM-F007'] = ControlResult(STATUS_PARTIAL, f'ATM covers {n_covered} of {total_items} catalog items ({rate*100:.1f}%) — below 85% target.', WHY['WM-F007'], SOURCES['WM-F007'])
            else:
                r['WM-F007'] = ControlResult(STATUS_FLAG, f'ATM covers only {n_covered} of {total_items} catalog items ({rate*100:.1f}%). Significant discovery coverage gap.', WHY['WM-F007'], SOURCES['WM-F007'])

    # ── WM-F008: Brand (BA) Layer Exists ─────────────────────────────────────
    ba_found = False
    if qt_camps is not None:
        type_col = _find_col(qt_camps, 'QuartileCampaignType', 'QT_Type', 'CampaignType')
        if type_col:
            ba_rows = qt_camps[qt_camps[type_col].astype(str).apply(lambda v: _type_matches(v, BA_TYPES))]
            ba_found = len(ba_rows) > 0
    if ba_found:
        r['WM-F008'] = ControlResult(STATUS_OK, 'Brand (BA) campaign layer is active. Branded search defense is in place.', WHY['WM-F008'], SOURCES['WM-F008'])
    else:
        r['WM-F008'] = ControlResult(STATUS_FLAG, 'No Brand (BA) campaign layer found. Competitors can capture branded search traffic without opposition.', WHY['WM-F008'], SOURCES['WM-F008'])

    # ── WM-F009: Auto vs Manual Spend Ratio ──────────────────────────────────
    if meta is None:
        r['WM-F009'] = ControlResult(STATUS_PARTIAL, 'Campaign metadata not available. Cannot compute auto/manual spend split.', WHY['WM-F009'], SOURCES['WM-F009'])
    else:
        tgt_col   = _find_col(meta, 'TargetingType', 'Targeting_Type', 'targeting')
        spend_col = _find_col(meta, 'Spend', 'AdSpend')
        camps_df  = _nonempty(ctx.df_campaigns)

        # Try to join spend from campaign report if meta doesn't have it
        if spend_col is None and camps_df is not None:
            camp_id_meta = _find_col(meta, 'CampaignId', 'Campaign_Id', 'campaignid')
            camp_id_rpt  = _find_col(camps_df, 'CampaignId', 'Campaign_Id', 'campaignid')
            spend_col_rpt = _find_col(camps_df, 'Spend', 'AdSpend')
            if all(v is not None for v in [camp_id_meta, camp_id_rpt, spend_col_rpt]):
                merged = meta.merge(camps_df[[camp_id_rpt, spend_col_rpt]], left_on=camp_id_meta, right_on=camp_id_rpt, how='left')
                meta = merged
                spend_col = spend_col_rpt

        if tgt_col is None or spend_col is None:
            r['WM-F009'] = ControlResult(STATUS_PARTIAL, 'TargetingType or spend data missing. Cannot compute auto/manual ratio.', WHY['WM-F009'], SOURCES['WM-F009'])
        else:
            meta2 = meta.copy()
            meta2['_spend'] = pd.to_numeric(meta2[spend_col], errors='coerce').fillna(0)
            auto_mask   = meta2[tgt_col].astype(str).str.lower().str.strip().isin(['auto', 'automatic', 'atm'])
            auto_spend  = meta2.loc[auto_mask, '_spend'].sum()
            total_spend = meta2['_spend'].sum()
            auto_pct    = auto_spend / total_spend if total_spend > 0 else 0.0

            if auto_pct <= 0.60:
                r['WM-F009'] = ControlResult(STATUS_OK, f'Auto campaigns account for {auto_pct*100:.1f}% of spend. Manual control is balanced at {(1-auto_pct)*100:.1f}%.', WHY['WM-F009'], SOURCES['WM-F009'])
            elif auto_pct <= 0.80:
                r['WM-F009'] = ControlResult(STATUS_PARTIAL, f'Auto campaigns account for {auto_pct*100:.1f}% of spend — above 60% threshold. Manual keyword control is insufficient.', WHY['WM-F009'], SOURCES['WM-F009'])
            else:
                r['WM-F009'] = ControlResult(STATUS_FLAG, f'Auto campaigns account for {auto_pct*100:.1f}% of spend. Manual bidding is almost absent — efficiency will degrade at scale.', WHY['WM-F009'], SOURCES['WM-F009'])

    # ── WM-F010: SV ROAS Check ────────────────────────────────────────────────
    if grp is None:
        r['WM-F010'] = ControlResult(STATUS_PARTIAL, 'Campaign group data not available. Cannot verify SV ROAS.', WHY['WM-F010'], SOURCES['WM-F010'])
    else:
        type_col  = _find_col(grp, 'CampaignType', 'Campaign_Type', 'Type')
        spend_col = _find_col(grp, 'Spend', 'AdSpend')
        sales_col = _find_col(grp, 'Sales', 'AdSales', 'Ad_Sales')

        if type_col is None:
            r['WM-F010'] = ControlResult(STATUS_PARTIAL, 'CampaignType column missing. Cannot verify SV ROAS.', WHY['WM-F010'], SOURCES['WM-F010'])
        else:
            sv_rows = grp[grp[type_col].astype(str).apply(lambda v: _type_matches(v, SV_TYPES))]
            if sv_rows.empty:
                r['WM-F010'] = ControlResult(STATUS_OK, 'No Sponsored Video campaigns found — no SV ROAS check required.', WHY['WM-F010'], SOURCES['WM-F010'])
            elif spend_col is None or sales_col is None:
                r['WM-F010'] = ControlResult(STATUS_PARTIAL, 'SV campaigns found but spend/sales columns missing. Cannot compute ROAS.', WHY['WM-F010'], SOURCES['WM-F010'])
            else:
                sv_spend = pd.to_numeric(sv_rows[spend_col], errors='coerce').fillna(0).sum()
                sv_sales = pd.to_numeric(sv_rows[sales_col], errors='coerce').fillna(0).sum()
                sv_roas  = sv_sales / sv_spend if sv_spend > 0 else 0.0

                if sv_roas >= 1.5:
                    r['WM-F010'] = ControlResult(STATUS_OK, f'SV ROAS is {sv_roas:.2f}x (${sv_spend:,.0f} spend, ${sv_sales:,.0f} sales). Above 1.5x threshold.', WHY['WM-F010'], SOURCES['WM-F010'])
                elif sv_roas > 0:
                    r['WM-F010'] = ControlResult(STATUS_PARTIAL, f'SV ROAS is {sv_roas:.2f}x — below 1.5x threshold. Review SV creative and targeting.', WHY['WM-F010'], SOURCES['WM-F010'])
                else:
                    r['WM-F010'] = ControlResult(STATUS_FLAG, f'SV campaigns have spend (${sv_spend:,.0f}) but zero attributed sales. Creative or attribution issue.', WHY['WM-F010'], SOURCES['WM-F010'])

    # ── WM-F011: Bidding Strategy Configured ─────────────────────────────────
    if meta is None:
        r['WM-F011'] = ControlResult(STATUS_FLAG, 'Campaign metadata not available. Cannot verify bidding strategy.', WHY['WM-F011'], SOURCES['WM-F011'])
    else:
        status_col = _find_col(meta, 'CampaignStatus', 'Status')
        bid_col    = _find_col(meta, 'BiddingStrategy', 'Bidding_Strategy', 'biddingstrategy')
        active     = meta[meta[status_col].astype(str).str.upper().str.strip() == 'ACTIVE'] if status_col else meta
        total      = len(active)

        if bid_col is None:
            r['WM-F011'] = ControlResult(STATUS_PARTIAL, f'{total} active campaigns found but BiddingStrategy column is missing. Cannot verify configuration.', WHY['WM-F011'], SOURCES['WM-F011'])
        else:
            null_mask = active[bid_col].isna() | (active[bid_col].astype(str).str.strip() == '')
            n_missing = null_mask.sum()
            if n_missing == 0:
                r['WM-F011'] = ControlResult(STATUS_OK, f'All {total} active campaigns have a bidding strategy configured.', WHY['WM-F011'], SOURCES['WM-F011'])
            elif n_missing / total <= 0.10:
                r['WM-F011'] = ControlResult(STATUS_PARTIAL, f'{n_missing} of {total} active campaigns are missing a bidding strategy ({n_missing/total*100:.1f}%). Minor gap.', WHY['WM-F011'], SOURCES['WM-F011'])
            else:
                r['WM-F011'] = ControlResult(STATUS_FLAG, f'{n_missing} of {total} active campaigns have no bidding strategy ({n_missing/total*100:.1f}%). Walmart is optimizing without direction on these campaigns.', WHY['WM-F011'], SOURCES['WM-F011'])

    # ── WM-F012: Advertised Item Coverage Rate ────────────────────────────────
    if catalog is None or ad_items is None:
        r['WM-F012'] = ControlResult(STATUS_FLAG, 'Product catalog or ad item data not available. Cannot compute coverage rate.', WHY['WM-F012'], SOURCES['WM-F012'])
    else:
        cat_id_col  = _find_col(catalog, 'ItemId', 'Item_Id', 'ITEM_ID', 'ProductId')
        item_id_col = _find_col(ad_items, 'ItemId', 'Item_Id', 'ITEM_ID')
        status_col  = _find_col(ad_items, 'ReviewStatus', 'Status', 'ItemStatus')

        if cat_id_col is None or item_id_col is None:
            r['WM-F012'] = ControlResult(STATUS_PARTIAL, 'ItemId columns missing. Cannot compute item coverage rate.', WHY['WM-F012'], SOURCES['WM-F012'])
        else:
            total_items = catalog[cat_id_col].dropna().nunique()
            active_ad_items = ad_items
            if status_col:
                active_ad_items = ad_items[ad_items[status_col].astype(str).str.upper().str.strip() == 'APPROVED']
            advertised_ids = active_ad_items[item_id_col].dropna().unique()
            n_covered = len(advertised_ids)
            rate = n_covered / total_items if total_items > 0 else 0.0

            if rate >= 0.80:
                r['WM-F012'] = ControlResult(STATUS_OK, f'{n_covered} of {total_items} catalog items have active ads ({rate*100:.1f}%). Coverage meets 80% threshold.', WHY['WM-F012'], SOURCES['WM-F012'])
            elif rate >= 0.50:
                r['WM-F012'] = ControlResult(STATUS_PARTIAL, f'{n_covered} of {total_items} catalog items have active ads ({rate*100:.1f}%) — below 80% target.', WHY['WM-F012'], SOURCES['WM-F012'])
            else:
                r['WM-F012'] = ControlResult(STATUS_FLAG, f'Only {n_covered} of {total_items} catalog items are advertised ({rate*100:.1f}%). Major item coverage gap.', WHY['WM-F012'], SOURCES['WM-F012'])

    # ── WM-F013: New Item Onboarding Velocity ─────────────────────────────────
    if catalog is None or ad_items is None:
        r['WM-F013'] = ControlResult(STATUS_PARTIAL, 'Product catalog or ad item data not available.', WHY['WM-F013'], SOURCES['WM-F013'])
    else:
        cat_id_col    = _find_col(catalog, 'ItemId', 'Item_Id', 'ITEM_ID')
        create_col    = _find_col(catalog, 'CreatedDate', 'ItemCreationDate', 'CreationDate', 'DateCreated')
        item_id_col   = _find_col(ad_items, 'ItemId', 'Item_Id', 'ITEM_ID')

        if create_col is None or cat_id_col is None or item_id_col is None:
            r['WM-F013'] = ControlResult(STATUS_PARTIAL, 'Creation date or item ID columns missing. Cannot assess onboarding velocity.', WHY['WM-F013'], SOURCES['WM-F013'])
        else:
            try:
                catalog2 = catalog.copy()
                catalog2['_created'] = pd.to_datetime(catalog2[create_col], errors='coerce')
                window_end = ctx.window_end
                if window_end:
                    cutoff = pd.Timestamp(window_end) - pd.Timedelta(days=30)
                    new_items = catalog2[catalog2['_created'] >= cutoff][cat_id_col].dropna().unique()
                    advertised = ad_items[item_id_col].dropna().unique()
                    onboarded  = set(new_items) & set(advertised)
                    total_new  = len(new_items)

                    if total_new == 0:
                        r['WM-F013'] = ControlResult(STATUS_OK, 'No new items created in the last 30 days. Onboarding velocity not applicable.', WHY['WM-F013'], SOURCES['WM-F013'])
                    elif len(onboarded) / total_new >= 0.80:
                        r['WM-F013'] = ControlResult(STATUS_OK, f'{len(onboarded)} of {total_new} new items ({len(onboarded)/total_new*100:.1f}%) onboarded within 30 days of creation.', WHY['WM-F013'], SOURCES['WM-F013'])
                    elif len(onboarded) > 0:
                        r['WM-F013'] = ControlResult(STATUS_PARTIAL, f'Only {len(onboarded)} of {total_new} new items ({len(onboarded)/total_new*100:.1f}%) onboarded within 30 days. New inventory not being monetized promptly.', WHY['WM-F013'], SOURCES['WM-F013'])
                    else:
                        r['WM-F013'] = ControlResult(STATUS_FLAG, f'{total_new} new items created in last 30 days but none added to active campaigns. New inventory not being monetized.', WHY['WM-F013'], SOURCES['WM-F013'])
                else:
                    r['WM-F013'] = ControlResult(STATUS_PARTIAL, 'Window end date not available. Cannot assess 30-day onboarding window.', WHY['WM-F013'], SOURCES['WM-F013'])
            except Exception as e:
                r['WM-F013'] = ControlResult(STATUS_PARTIAL, f'Could not compute item onboarding velocity: {str(e)[:80]}', WHY['WM-F013'], SOURCES['WM-F013'])

    # ── WM-F014: Item Review Status Health ───────────────────────────────────
    if ad_items is None:
        r['WM-F014'] = ControlResult(STATUS_FLAG, 'Ad item data not available.', WHY['WM-F014'], SOURCES['WM-F014'])
    else:
        status_col = _find_col(ad_items, 'ReviewStatus', 'Status', 'ItemStatus')
        if status_col is None:
            r['WM-F014'] = ControlResult(STATUS_PARTIAL, 'ReviewStatus column not found in ad item data.', WHY['WM-F014'], SOURCES['WM-F014'])
        else:
            total     = len(ad_items)
            approved  = (ad_items[status_col].astype(str).str.upper().str.strip() == 'APPROVED').sum()
            rejected  = (ad_items[status_col].astype(str).str.upper().str.strip() == 'REJECTED').sum()
            rej_rate  = rejected / total if total > 0 else 0.0

            if rej_rate == 0:
                r['WM-F014'] = ControlResult(STATUS_OK, f'All {total} ad items are APPROVED. No rejected items found.', WHY['WM-F014'], SOURCES['WM-F014'])
            elif rej_rate <= 0.10:
                r['WM-F014'] = ControlResult(STATUS_PARTIAL, f'{rejected} of {total} ad items are REJECTED ({rej_rate*100:.1f}%). Minor rejection rate — review and resolve.', WHY['WM-F014'], SOURCES['WM-F014'])
            else:
                r['WM-F014'] = ControlResult(STATUS_FLAG, f'{rejected} of {total} ad items are REJECTED ({rej_rate*100:.1f}%). High rejection rate is blocking effective ad serving.', WHY['WM-F014'], SOURCES['WM-F014'])

    # ── WM-F015: Item Availability & Publish Status ───────────────────────────
    if catalog is None or ad_items is None:
        r['WM-F015'] = ControlResult(STATUS_FLAG, 'Product catalog or ad item data not available.', WHY['WM-F015'], SOURCES['WM-F015'])
    else:
        cat_id_col   = _find_col(catalog, 'ItemId', 'Item_Id', 'ITEM_ID')
        item_id_col  = _find_col(ad_items, 'ItemId', 'Item_Id', 'ITEM_ID')
        avail_col    = _find_col(catalog, 'AvailabilityStatus', 'Availability', 'availability')
        publish_col  = _find_col(catalog, 'PublishedStatus', 'Published', 'publishedstatus')

        if cat_id_col is None or item_id_col is None:
            r['WM-F015'] = ControlResult(STATUS_PARTIAL, 'ItemId columns missing. Cannot assess availability/publish status.', WHY['WM-F015'], SOURCES['WM-F015'])
        elif avail_col is None and publish_col is None:
            r['WM-F015'] = ControlResult(STATUS_PARTIAL, 'AvailabilityStatus and PublishedStatus columns not found in catalog.', WHY['WM-F015'], SOURCES['WM-F015'])
        else:
            advertised_ids = set(ad_items[item_id_col].dropna().astype(str))
            advertised_catalog = catalog[catalog[cat_id_col].astype(str).isin(advertised_ids)]
            total = len(advertised_catalog)
            n_unavail = n_unpublished = 0
            if avail_col:
                n_unavail = (advertised_catalog[avail_col].astype(str).str.upper().str.strip() != 'AVAILABLE').sum()
            if publish_col:
                n_unpublished = (advertised_catalog[publish_col].astype(str).str.upper().str.strip() != 'PUBLISHED').sum()

            bad_total = max(n_unavail, n_unpublished)
            if bad_total == 0:
                r['WM-F015'] = ControlResult(STATUS_OK, f'All {total} advertised items are AVAILABLE and PUBLISHED. No wasted ad spend on unavailable items.', WHY['WM-F015'], SOURCES['WM-F015'])
            elif bad_total / total <= 0.05:
                r['WM-F015'] = ControlResult(STATUS_PARTIAL, f'{bad_total} of {total} advertised items ({bad_total/total*100:.1f}%) are unavailable or unpublished. Minor issue.', WHY['WM-F015'], SOURCES['WM-F015'])
            else:
                r['WM-F015'] = ControlResult(STATUS_FLAG, f'{bad_total} of {total} advertised items ({bad_total/total*100:.1f}%) are unavailable or unpublished. Ad spend is being wasted on non-serving items.', WHY['WM-F015'], SOURCES['WM-F015'])

    # ── WM-F016: Zero-Inventory Items with Active Ad Spend ────────────────────
    if catalog is None or ad_items is None:
        r['WM-F016'] = ControlResult(STATUS_FLAG, 'Product catalog or ad item data not available.', WHY['WM-F016'], SOURCES['WM-F016'])
    else:
        cat_id_col  = _find_col(catalog, 'ItemId', 'Item_Id', 'ITEM_ID')
        item_id_col = _find_col(ad_items, 'ItemId', 'Item_Id', 'ITEM_ID')
        inv_col     = _find_col(catalog, 'InventoryCount', 'Inventory', 'inventory_count')

        if cat_id_col is None or item_id_col is None or inv_col is None:
            r['WM-F016'] = ControlResult(STATUS_PARTIAL, 'ItemId or InventoryCount columns missing. Cannot verify zero-inventory ad spend.', WHY['WM-F016'], SOURCES['WM-F016'])
        else:
            catalog2 = catalog.copy()
            catalog2['_inv'] = pd.to_numeric(catalog2[inv_col], errors='coerce').fillna(0)
            zero_inv_ids = set(catalog2[catalog2['_inv'] == 0][cat_id_col].astype(str))
            advertised   = set(ad_items[item_id_col].dropna().astype(str))
            wasted_ids   = zero_inv_ids & advertised
            n_wasted     = len(wasted_ids)

            if n_wasted == 0:
                r['WM-F016'] = ControlResult(STATUS_OK, 'No zero-inventory items are receiving ad spend. All advertised items have available inventory.', WHY['WM-F016'], SOURCES['WM-F016'])
            elif n_wasted <= 3:
                r['WM-F016'] = ControlResult(STATUS_PARTIAL, f'{n_wasted} item(s) with zero inventory are still active in campaigns. Remove or pause these items immediately.', WHY['WM-F016'], SOURCES['WM-F016'])
            else:
                r['WM-F016'] = ControlResult(STATUS_FLAG, f'{n_wasted} items with zero inventory are receiving ad spend. This is direct budget waste with zero conversion potential.', WHY['WM-F016'], SOURCES['WM-F016'])

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
    grade = 'Is Compliant' if score >= 75 else ('Need Improvement' if score >= 40 else 'Non-Compliant')
    findings.sort(key=lambda x: (0 if x['status'] == STATUS_FLAG else 1 if x['status'] == STATUS_PARTIAL else 2, x['penalty']))
    return total_penalty, score, grade, findings


def interpretation(grade: str) -> str:
    return {
        'Is Compliant': 'The account framework is compliant. Core governance controls are correctly configured, enabling stable optimization and scalable performance.',
        'Need Improvement': 'Structural deviations were identified that limit full system governance. Remediation is required before scaling.',
        'Non-Compliant': 'Critical framework gaps were identified that materially restrict system control and optimization. Immediate remediation is required prior to any scaling activity.',
    }.get(grade, '')
