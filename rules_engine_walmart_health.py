from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from config_walmart_health import (
    CONTROL_NAMES, IMPACT_LABEL, IMPORTANCE, PRIORITY_POINTS,
    SOURCES, STATUS_FLAG, STATUS_OK, STATUS_PARTIAL, VISIBILITY_ONLY,
    WHY, ControlResult,
)
from reader_databricks_walmart import WalmartContext, clean_text, norm_pct, pct_str, to_float, _find_col


def _nonempty(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None
    tmp = df.dropna(how='all')
    return tmp if not tmp.empty else None


def _pct_change(curr: Optional[float], prev: Optional[float]) -> Optional[float]:
    if curr is None or prev is None or prev == 0:
        return None
    return (curr - prev) / abs(prev)


def evaluate_all(ctx: WalmartContext) -> Dict[str, ControlResult]:
    r: Dict[str, ControlResult] = {}

    # ── WM-H001: ACoS vs Project ──────────────────────────────────────────────
    acos   = ctx.acos
    target = ctx.proj_acos_target

    if acos is None:
        r['WM-H001'] = ControlResult(STATUS_FLAG, 'ACoS data not found in 02_Date_Range_KPIs.', WHY['WM-H001'], SOURCES['WM-H001'])
    elif target is None:
        r['WM-H001'] = ControlResult(STATUS_PARTIAL, f'Current ACoS: {pct_str(acos)}. No ACoS target documented in project dataset — cannot evaluate against goal.', WHY['WM-H001'], SOURCES['WM-H001'])
    else:
        dev = (acos - target) / target if target > 0 else 0.0
        if dev <= 0.05:
            r['WM-H001'] = ControlResult(STATUS_OK, f'ACoS: {pct_str(acos)} vs target {pct_str(target)} — within 5% of target. Efficiency is on track.', WHY['WM-H001'], SOURCES['WM-H001'])
        elif dev <= 0.20:
            r['WM-H001'] = ControlResult(STATUS_PARTIAL, f'ACoS: {pct_str(acos)} vs target {pct_str(target)} — {dev*100:.1f}% above target. Monitor closely.', WHY['WM-H001'], SOURCES['WM-H001'])
        else:
            r['WM-H001'] = ControlResult(STATUS_FLAG, f'ACoS: {pct_str(acos)} vs target {pct_str(target)} — {dev*100:.1f}% above target. Immediate diagnosis required.', WHY['WM-H001'], SOURCES['WM-H001'])

    # ── WM-H002: TACoS vs Project ─────────────────────────────────────────────
    tacos  = ctx.tacos
    ttarget = ctx.proj_tacos_target

    if tacos is None:
        r['WM-H002'] = ControlResult(STATUS_FLAG, 'TACoS data not found in 02_Date_Range_KPIs.', WHY['WM-H002'], SOURCES['WM-H002'])
    elif ttarget is None:
        r['WM-H002'] = ControlResult(STATUS_PARTIAL, f'Current TACoS: {pct_str(tacos)}. No TACoS target documented — cannot evaluate against goal.', WHY['WM-H002'], SOURCES['WM-H002'])
    else:
        dev = (tacos - ttarget) / ttarget if ttarget > 0 else 0.0
        if dev <= 0:
            r['WM-H002'] = ControlResult(STATUS_OK, f'TACoS: {pct_str(tacos)} vs target {pct_str(ttarget)} — at or below target.', WHY['WM-H002'], SOURCES['WM-H002'])
        elif dev <= 0.10:
            r['WM-H002'] = ControlResult(STATUS_PARTIAL, f'TACoS: {pct_str(tacos)} vs target {pct_str(ttarget)} — {dev*100:.1f}% above target. Organic lift may be weakening.', WHY['WM-H002'], SOURCES['WM-H002'])
        else:
            r['WM-H002'] = ControlResult(STATUS_FLAG, f'TACoS: {pct_str(tacos)} vs target {pct_str(ttarget)} — {dev*100:.1f}% above target. Advertising is not generating organic lift at the required rate.', WHY['WM-H002'], SOURCES['WM-H002'])

    # ── WM-H003: ROAS Trend ───────────────────────────────────────────────────
    roas      = ctx.roas
    prev_roas = ctx.prev_roas
    chg       = _pct_change(roas, prev_roas)

    if roas is None:
        r['WM-H003'] = ControlResult(STATUS_FLAG, 'ROAS data not available in 02_Date_Range_KPIs.', WHY['WM-H003'], SOURCES['WM-H003'])
    elif prev_roas is None or chg is None:
        r['WM-H003'] = ControlResult(STATUS_PARTIAL, f'Current ROAS: {roas:.2f}x. Prior period ROAS not available — trend cannot be computed.', WHY['WM-H003'], SOURCES['WM-H003'])
    elif chg >= -0.05:
        r['WM-H003'] = ControlResult(STATUS_OK, f'ROAS: {roas:.2f}x vs {prev_roas:.2f}x prior period ({chg*100:+.1f}%). Trend is stable.', WHY['WM-H003'], SOURCES['WM-H003'])
    elif chg >= -0.15:
        r['WM-H003'] = ControlResult(STATUS_PARTIAL, f'ROAS: {roas:.2f}x vs {prev_roas:.2f}x ({chg*100:+.1f}%). Moderate decline — monitor for continuation.', WHY['WM-H003'], SOURCES['WM-H003'])
    else:
        r['WM-H003'] = ControlResult(STATUS_FLAG, f'ROAS: {roas:.2f}x vs {prev_roas:.2f}x ({chg*100:+.1f}%). ROAS decline exceeds 15% threshold. Structural review required.', WHY['WM-H003'], SOURCES['WM-H003'])

    # ── WM-H004: Sales Trend ──────────────────────────────────────────────────
    sales      = ctx.ad_sales
    prev_sales = ctx.prev_ad_sales
    chg_s      = _pct_change(sales, prev_sales)

    if sales is None:
        r['WM-H004'] = ControlResult(STATUS_FLAG, 'Ad sales data not available.', WHY['WM-H004'], SOURCES['WM-H004'])
    elif chg_s is None:
        r['WM-H004'] = ControlResult(STATUS_PARTIAL, f'Current ad sales: ${sales:,.0f}. Prior period not available — trend cannot be computed.', WHY['WM-H004'], SOURCES['WM-H004'])
    elif chg_s >= -0.05:
        r['WM-H004'] = ControlResult(STATUS_OK, f'Ad sales: ${sales:,.0f} vs ${prev_sales:,.0f} prior period ({chg_s*100:+.1f}%). Sales trend is stable.', WHY['WM-H004'], SOURCES['WM-H004'])
    elif chg_s >= -0.10:
        r['WM-H004'] = ControlResult(STATUS_PARTIAL, f'Ad sales: ${sales:,.0f} vs ${prev_sales:,.0f} ({chg_s*100:+.1f}%). Moderate sales decline — investigate root cause.', WHY['WM-H004'], SOURCES['WM-H004'])
    else:
        r['WM-H004'] = ControlResult(STATUS_FLAG, f'Ad sales: ${sales:,.0f} vs ${prev_sales:,.0f} ({chg_s*100:+.1f}%). Sales decline exceeds 10% threshold. Immediate root cause investigation required.', WHY['WM-H004'], SOURCES['WM-H004'])

    # ── WM-H005: Paid Dependency ──────────────────────────────────────────────
    ad_s    = ctx.ad_sales
    total_s = ctx.total_sales

    if ad_s is None or total_s is None or total_s == 0:
        r['WM-H005'] = ControlResult(STATUS_PARTIAL, 'Ad sales or total sales data not available. Cannot compute paid dependency ratio.', WHY['WM-H005'], SOURCES['WM-H005'])
    else:
        dep = ad_s / total_s
        if dep <= 0.50:
            r['WM-H005'] = ControlResult(STATUS_OK, f'Paid dependency: {dep*100:.1f}% (${ad_s:,.0f} ad sales / ${total_s:,.0f} total sales). Organic base is healthy.', WHY['WM-H005'], SOURCES['WM-H005'])
        elif dep <= 0.70:
            r['WM-H005'] = ControlResult(STATUS_PARTIAL, f'Paid dependency: {dep*100:.1f}%. Above 50% — organic rank may be weakening. Monitor trend.', WHY['WM-H005'], SOURCES['WM-H005'])
        else:
            r['WM-H005'] = ControlResult(STATUS_FLAG, f'Paid dependency: {dep*100:.1f}%. Above 70% threshold — account is unsustainably reliant on ad spend for revenue generation.', WHY['WM-H005'], SOURCES['WM-H005'])

    # ── WM-H006: CTR Performance ──────────────────────────────────────────────
    ctr      = ctx.ctr
    prev_ctr = ctx.prev_ctr
    chg_c    = _pct_change(ctr, prev_ctr)

    if ctr is None:
        r['WM-H006'] = ControlResult(STATUS_FLAG, 'CTR data not available.', WHY['WM-H006'], SOURCES['WM-H006'])
    elif chg_c is None:
        r['WM-H006'] = ControlResult(STATUS_PARTIAL, f'Current CTR: {pct_str(ctr)}. Prior period not available — trend cannot be computed.', WHY['WM-H006'], SOURCES['WM-H006'])
    elif chg_c >= -0.10:
        r['WM-H006'] = ControlResult(STATUS_OK, f'CTR: {pct_str(ctr)} vs {pct_str(prev_ctr)} ({chg_c*100:+.1f}%). CTR is stable.', WHY['WM-H006'], SOURCES['WM-H006'])
    elif chg_c >= -0.20:
        r['WM-H006'] = ControlResult(STATUS_PARTIAL, f'CTR: {pct_str(ctr)} vs {pct_str(prev_ctr)} ({chg_c*100:+.1f}%). Moderate CTR decline — review creative and placements.', WHY['WM-H006'], SOURCES['WM-H006'])
    else:
        r['WM-H006'] = ControlResult(STATUS_FLAG, f'CTR: {pct_str(ctr)} vs {pct_str(prev_ctr)} ({chg_c*100:+.1f}%). CTR decline exceeds 20% — creative fatigue or relevance issue.', WHY['WM-H006'], SOURCES['WM-H006'])

    # ── WM-H007: CVR Health ───────────────────────────────────────────────────
    cvr      = ctx.cvr
    prev_cvr = ctx.prev_cvr
    chg_v    = _pct_change(cvr, prev_cvr)

    if cvr is None:
        r['WM-H007'] = ControlResult(STATUS_FLAG, 'CVR data not available.', WHY['WM-H007'], SOURCES['WM-H007'])
    elif chg_v is None:
        r['WM-H007'] = ControlResult(STATUS_PARTIAL, f'Current CVR: {pct_str(cvr)}. Prior period not available — trend cannot be computed.', WHY['WM-H007'], SOURCES['WM-H007'])
    elif chg_v >= -0.08:
        r['WM-H007'] = ControlResult(STATUS_OK, f'CVR: {pct_str(cvr)} vs {pct_str(prev_cvr)} ({chg_v*100:+.1f}%). CVR is stable.', WHY['WM-H007'], SOURCES['WM-H007'])
    elif chg_v >= -0.15:
        r['WM-H007'] = ControlResult(STATUS_PARTIAL, f'CVR: {pct_str(cvr)} vs {pct_str(prev_cvr)} ({chg_v*100:+.1f}%). Moderate decline — check pricing, buy box, and reviews.', WHY['WM-H007'], SOURCES['WM-H007'])
    else:
        r['WM-H007'] = ControlResult(STATUS_FLAG, f'CVR: {pct_str(cvr)} vs {pct_str(prev_cvr)} ({chg_v*100:+.1f}%). CVR decline exceeds 15% — likely pricing or listing quality issue.', WHY['WM-H007'], SOURCES['WM-H007'])

    # ── WM-H008: CPC Trend (Visibility) ──────────────────────────────────────
    cpc      = ctx.cpc
    prev_cpc = ctx.prev_cpc
    chg_cpc  = _pct_change(cpc, prev_cpc)

    if cpc is None:
        r['WM-H008'] = ControlResult(STATUS_OK, 'CPC data not available. Visibility metric — no scoring impact.', WHY['WM-H008'], SOURCES['WM-H008'])
    elif chg_cpc is None:
        r['WM-H008'] = ControlResult(STATUS_OK, f'CPC: ${cpc:.2f}. Prior period not available. Visibility metric.', WHY['WM-H008'], SOURCES['WM-H008'])
    else:
        direction = 'up' if chg_cpc > 0 else 'down'
        r['WM-H008'] = ControlResult(STATUS_OK, f'CPC: ${cpc:.2f} vs ${prev_cpc:.2f} ({chg_cpc*100:+.1f}%, {direction}). Visibility metric — review if CPC increase aligns with performance.', WHY['WM-H008'], SOURCES['WM-H008'])

    # ── WM-H009: YoY Trajectory (Visibility) ─────────────────────────────────
    df_yoy = _nonempty(ctx.df_yearly)
    if df_yoy is None:
        r['WM-H009'] = ControlResult(STATUS_OK, 'YoY data not available. Visibility metric.', WHY['WM-H009'], SOURCES['WM-H009'])
    else:
        spend_col = _find_col(df_yoy, 'CurrentSpend', 'ThisYearSpend', 'Spend', 'AdSpend')
        sales_col = _find_col(df_yoy, 'CurrentSales', 'ThisYearSales', 'Sales', 'AdSales')
        prev_spend_col = _find_col(df_yoy, 'LastYearSpend', 'PrevSpend', 'Prev_Spend')
        prev_sales_col = _find_col(df_yoy, 'LastYearSales', 'PrevSales', 'Prev_Sales')

        if all(c is not None for c in [spend_col, sales_col, prev_spend_col, prev_sales_col]):
            row = df_yoy.iloc[0]
            cy_spend = to_float(row[spend_col]);  ly_spend = to_float(row[prev_spend_col])
            cy_sales = to_float(row[sales_col]);  ly_sales = to_float(row[prev_sales_col])
            spend_g = _pct_change(cy_spend, ly_spend)
            sales_g = _pct_change(cy_sales, ly_sales)
            msg = f'Spend YoY: {spend_g*100:+.1f}% | Sales YoY: {sales_g*100:+.1f}%.' if spend_g is not None and sales_g is not None else 'Partial YoY data available.'
        else:
            msg = 'YoY columns found but key fields are missing.'
        r['WM-H009'] = ControlResult(STATUS_OK, f'{msg} Visibility metric.', WHY['WM-H009'], SOURCES['WM-H009'])

    # ── WM-H010: High-Spend Zero-Order Keywords (Visibility) ─────────────────
    df_kw = _nonempty(ctx.df_keywords)
    if df_kw is None:
        r['WM-H010'] = ControlResult(STATUS_OK, 'Keyword performance data not available. Visibility metric.', WHY['WM-H010'], SOURCES['WM-H010'])
    else:
        spend_col  = _find_col(df_kw, 'AdSpend', 'Spend', 'spend')
        orders_col = _find_col(df_kw, 'Orders', 'orders', 'Purchases')
        if spend_col and orders_col:
            df_kw2 = df_kw.copy()
            df_kw2['_spend']  = pd.to_numeric(df_kw2[spend_col], errors='coerce').fillna(0)
            df_kw2['_orders'] = pd.to_numeric(df_kw2[orders_col], errors='coerce').fillna(0)
            threshold = df_kw2['_spend'].quantile(0.75) if len(df_kw2) > 10 else 5.0
            wasted = df_kw2[(df_kw2['_spend'] >= threshold) & (df_kw2['_orders'] == 0)]
            r['WM-H010'] = ControlResult(STATUS_OK, f'{len(wasted)} keywords with significant spend and zero orders detected. Visibility metric — review and negate manually.', WHY['WM-H010'], SOURCES['WM-H010'])
        else:
            r['WM-H010'] = ControlResult(STATUS_OK, 'Spend or orders columns not found in keyword data. Visibility metric.', WHY['WM-H010'], SOURCES['WM-H010'])

    # ── WM-H011: Match Type ACoS Floor (Visibility) ───────────────────────────
    if df_kw is None:
        r['WM-H011'] = ControlResult(STATUS_OK, 'Keyword data not available. Visibility metric.', WHY['WM-H011'], SOURCES['WM-H011'])
    else:
        match_col = _find_col(df_kw, 'MatchType', 'Match_Type', 'matchtype')
        spend_col = _find_col(df_kw, 'AdSpend', 'Spend')
        sales_col = _find_col(df_kw, 'AdSales', 'Sales')
        if match_col and spend_col and sales_col:
            df_kw3 = df_kw.copy()
            df_kw3['_spend'] = pd.to_numeric(df_kw3[spend_col], errors='coerce').fillna(0)
            df_kw3['_sales'] = pd.to_numeric(df_kw3[sales_col], errors='coerce').fillna(0)
            grp = df_kw3.groupby(match_col)[['_spend', '_sales']].sum()
            overbudget = []
            for mt, row in grp.iterrows():
                if row['_sales'] > 0:
                    acos_mt = row['_spend'] / row['_sales']
                    if acos_mt > 1.0:
                        overbudget.append(f'{mt}: ACoS {acos_mt*100:.0f}%')
            if overbudget:
                r['WM-H011'] = ControlResult(STATUS_OK, f'Match type(s) above 100% ACoS: {", ".join(overbudget)}. Visibility metric — review bids.', WHY['WM-H011'], SOURCES['WM-H011'])
            else:
                r['WM-H011'] = ControlResult(STATUS_OK, 'All match types are below 100% ACoS. Visibility metric — no action required.', WHY['WM-H011'], SOURCES['WM-H011'])
        else:
            r['WM-H011'] = ControlResult(STATUS_OK, 'Match type or spend/sales columns not available. Visibility metric.', WHY['WM-H011'], SOURCES['WM-H011'])

    # ── WM-H012: Product Rating Health (Visibility) ───────────────────────────
    catalog = _nonempty(ctx.df_product_catalog)
    ad_items = _nonempty(ctx.df_ad_items)
    if catalog is None:
        r['WM-H012'] = ControlResult(STATUS_OK, 'Product catalog not available. Visibility metric.', WHY['WM-H012'], SOURCES['WM-H012'])
    else:
        rating_col = _find_col(catalog, 'AverageRating', 'Rating', 'average_rating')
        if rating_col is None:
            r['WM-H012'] = ControlResult(STATUS_OK, 'AverageRating column not found in catalog. Visibility metric.', WHY['WM-H012'], SOURCES['WM-H012'])
        else:
            cat2 = catalog.copy()
            cat2['_rating'] = pd.to_numeric(cat2[rating_col], errors='coerce')
            valid = cat2.dropna(subset=['_rating'])
            if valid.empty:
                r['WM-H012'] = ControlResult(STATUS_OK, 'No rating data found. Visibility metric.', WHY['WM-H012'], SOURCES['WM-H012'])
            else:
                pct_good = (valid['_rating'] >= 4.0).sum() / len(valid)
                r['WM-H012'] = ControlResult(STATUS_OK, f'{pct_good*100:.1f}% of items have AverageRating >= 4.0. Visibility metric — items below 4.0 risk CVR suppression.', WHY['WM-H012'], SOURCES['WM-H012'])

    # ── WM-H013: Product Review Floor ─────────────────────────────────────────
    if catalog is None:
        r['WM-H013'] = ControlResult(STATUS_FLAG, 'Product catalog not available. Cannot assess review floor.', WHY['WM-H013'], SOURCES['WM-H013'])
    else:
        review_col = _find_col(catalog, 'ReviewCount', 'Review_Count', 'NumReviews', 'reviews')
        if review_col is None:
            r['WM-H013'] = ControlResult(STATUS_PARTIAL, 'ReviewCount column not found in product catalog.', WHY['WM-H013'], SOURCES['WM-H013'])
        else:
            cat3 = catalog.copy()
            cat3['_reviews'] = pd.to_numeric(cat3[review_col], errors='coerce').fillna(0)
            total = len(cat3)
            pct_ok = (cat3['_reviews'] >= 10).sum() / total if total > 0 else 0.0
            if pct_ok >= 0.80:
                r['WM-H013'] = ControlResult(STATUS_OK, f'{pct_ok*100:.1f}% of advertised items have >= 10 reviews. Review floor is healthy.', WHY['WM-H013'], SOURCES['WM-H013'])
            elif pct_ok >= 0.60:
                r['WM-H013'] = ControlResult(STATUS_PARTIAL, f'Only {pct_ok*100:.1f}% of items have >= 10 reviews — below 80% threshold. Items with thin reviews risk low CVR.', WHY['WM-H013'], SOURCES['WM-H013'])
            else:
                r['WM-H013'] = ControlResult(STATUS_FLAG, f'Only {pct_ok*100:.1f}% of items have >= 10 reviews. Ad spend on under-reviewed items is premature.', WHY['WM-H013'], SOURCES['WM-H013'])

    # ── WM-H014: Buybox Pricing (Visibility) ──────────────────────────────────
    if catalog is None:
        r['WM-H014'] = ControlResult(STATUS_OK, 'Product catalog not available. Visibility metric.', WHY['WM-H014'], SOURCES['WM-H014'])
    else:
        price_col  = _find_col(catalog, 'Price', 'ItemPrice', 'item_price')
        buybox_col = _find_col(catalog, 'BuyboxWinnerPrice', 'BuyBox_Winner_Price', 'buyboxwinprice')
        if price_col and buybox_col:
            cat4 = catalog.copy()
            cat4['_price']  = pd.to_numeric(cat4[price_col], errors='coerce')
            cat4['_buybox'] = pd.to_numeric(cat4[buybox_col], errors='coerce')
            valid = cat4.dropna(subset=['_price', '_buybox'])
            n_losing = (valid['_price'] > valid['_buybox']).sum()
            r['WM-H014'] = ControlResult(STATUS_OK, f'{n_losing} advertised items have a price above the current buy box winner price. Visibility metric — these items will not convert.', WHY['WM-H014'], SOURCES['WM-H014'])
        else:
            r['WM-H014'] = ControlResult(STATUS_OK, 'Price or BuyboxWinnerPrice columns not found. Visibility metric.', WHY['WM-H014'], SOURCES['WM-H014'])

    # ── WM-H015: Cancellation Rate (Visibility) ───────────────────────────────
    orders = _nonempty(ctx.df_marketplace_orders)
    if orders is None:
        r['WM-H015'] = ControlResult(STATUS_OK, 'Marketplace orders data not available. Visibility metric.', WHY['WM-H015'], SOURCES['WM-H015'])
    else:
        status_col = _find_col(orders, 'OrderLineStatus', 'Status', 'order_status')
        if status_col:
            total_orders = len(orders)
            cancelled = (orders[status_col].astype(str).str.upper().str.strip().isin(['CANCELLED', 'CANCELED'])).sum()
            cancel_rate = cancelled / total_orders if total_orders > 0 else 0.0
            r['WM-H015'] = ControlResult(STATUS_OK, f'Cancellation rate: {cancel_rate*100:.1f}% ({cancelled} of {total_orders} orders). Visibility metric — flag if > 3%.', WHY['WM-H015'], SOURCES['WM-H015'])
        else:
            r['WM-H015'] = ControlResult(STATUS_OK, 'OrderLineStatus column not found. Visibility metric.', WHY['WM-H015'], SOURCES['WM-H015'])

    # ── WM-H016: 2-Day Shipping Rate (Visibility) ─────────────────────────────
    if orders is None:
        r['WM-H016'] = ControlResult(STATUS_OK, 'Marketplace orders data not available. Visibility metric.', WHY['WM-H016'], SOURCES['WM-H016'])
    else:
        ship_col = _find_col(orders, 'ShippingProgramType', 'Shipping_Program', 'FulfillmentType')
        if ship_col:
            total = len(orders)
            two_day = orders[ship_col].astype(str).str.lower().str.contains('2.day|twoday|2day|express', na=False).sum()
            rate = two_day / total if total > 0 else 0.0
            r['WM-H016'] = ControlResult(STATUS_OK, f'2-day shipping rate: {rate*100:.1f}% ({two_day} of {total} orders). Visibility metric — target >50% for non-bulky categories.', WHY['WM-H016'], SOURCES['WM-H016'])
        else:
            r['WM-H016'] = ControlResult(STATUS_OK, 'ShippingProgramType column not found. Visibility metric.', WHY['WM-H016'], SOURCES['WM-H016'])

    # ── WM-H017: Refund Rate (Visibility) ─────────────────────────────────────
    if orders is None:
        r['WM-H017'] = ControlResult(STATUS_OK, 'Marketplace orders data not available. Visibility metric.', WHY['WM-H017'], SOURCES['WM-H017'])
    else:
        total_col  = _find_col(orders, 'TotalChargeAmount', 'TotalCharge', 'Revenue')
        refund_col = _find_col(orders, 'Refunds_TotalChargeAmount', 'RefundAmount', 'Refunds')
        if total_col and refund_col:
            total_rev   = pd.to_numeric(orders[total_col], errors='coerce').fillna(0).sum()
            total_ref   = pd.to_numeric(orders[refund_col], errors='coerce').fillna(0).sum()
            refund_rate = abs(total_ref) / total_rev if total_rev > 0 else 0.0
            r['WM-H017'] = ControlResult(STATUS_OK, f'Refund rate: {refund_rate*100:.1f}% (${abs(total_ref):,.0f} of ${total_rev:,.0f}). Visibility metric — flag if > 5%.', WHY['WM-H017'], SOURCES['WM-H017'])
        else:
            r['WM-H017'] = ControlResult(STATUS_OK, 'Refund amount columns not found in order data. Visibility metric.', WHY['WM-H017'], SOURCES['WM-H017'])

    # ── WM-H018: Product-Level ACoS Outliers (Visibility) ────────────────────
    df_pacos = _nonempty(ctx.df_product_acos)
    if df_pacos is None:
        r['WM-H018'] = ControlResult(STATUS_OK, 'Product-level ACoS data not available. Visibility metric.', WHY['WM-H018'], SOURCES['WM-H018'])
    else:
        acos_col = _find_col(df_pacos, 'ACoS_Percent', 'ACoS', 'acos', 'ACoSPercent')
        target   = ctx.proj_acos_target
        if acos_col and target:
            df_p2 = df_pacos.copy()
            df_p2['_acos'] = pd.to_numeric(df_p2[acos_col], errors='coerce')
            df_p2 = df_p2.dropna(subset=['_acos'])
            if not df_p2.empty:
                df_p2['_acos_norm'] = df_p2['_acos'].apply(lambda x: x / 100 if x > 1 else x)
                outliers = (df_p2['_acos_norm'] > target * 2).sum()
                r['WM-H018'] = ControlResult(STATUS_OK, f'{outliers} product(s) with ACoS > 2x account target ({pct_str(target*2)}). Visibility metric — review and adjust bids for outliers.', WHY['WM-H018'], SOURCES['WM-H018'])
            else:
                r['WM-H018'] = ControlResult(STATUS_OK, 'Product ACoS data present but no parseable values. Visibility metric.', WHY['WM-H018'], SOURCES['WM-H018'])
        else:
            r['WM-H018'] = ControlResult(STATUS_OK, 'ACoS column or account target not available for product-level comparison. Visibility metric.', WHY['WM-H018'], SOURCES['WM-H018'])

    # ── WM-H019: Monthly Spend Trend (Visibility) ─────────────────────────────
    df_l24m = _nonempty(ctx.df_l24m)
    if df_l24m is None:
        r['WM-H019'] = ControlResult(STATUS_OK, 'L24M monthly data not available. Visibility metric.', WHY['WM-H019'], SOURCES['WM-H019'])
    else:
        spend_col = _find_col(df_l24m, 'Spend', 'AdSpend', 'MonthlySpend')
        if spend_col:
            monthly = pd.to_numeric(df_l24m[spend_col], errors='coerce').dropna()
            if len(monthly) >= 3:
                last3  = monthly.tail(3).mean()
                prev3  = monthly.iloc[-6:-3].mean() if len(monthly) >= 6 else monthly.head(3).mean()
                chg_m  = _pct_change(last3, prev3)
                direction = 'up' if chg_m and chg_m > 0 else 'down'
                r['WM-H019'] = ControlResult(STATUS_OK, f'L3M avg spend: ${last3:,.0f} vs prior 3M avg: ${prev3:,.0f} ({(chg_m or 0)*100:+.1f}%, {direction}). Visibility metric.', WHY['WM-H019'], SOURCES['WM-H019'])
            else:
                r['WM-H019'] = ControlResult(STATUS_OK, f'L24M data has fewer than 3 months. Visibility metric.', WHY['WM-H019'], SOURCES['WM-H019'])
        else:
            r['WM-H019'] = ControlResult(STATUS_OK, 'Spend column not found in L24M data. Visibility metric.', WHY['WM-H019'], SOURCES['WM-H019'])

    return r


def compute_score(results: Dict[str, ControlResult]):
    findings = []
    total_penalty = 0.0

    for cid, res in results.items():
        imp = IMPORTANCE[cid]
        pen = 0.0
        if cid not in VISIBILITY_ONLY:
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
            'impact': 'Visibility' if cid in VISIBILITY_ONLY else IMPACT_LABEL[imp],
            'penalty': pen,
        })

    score = 100 + total_penalty
    grade = 'Healthy' if score >= 75 else ('Needs Attention' if score >= 40 else 'At Risk')
    findings.sort(key=lambda x: (0 if x['status'] == STATUS_FLAG else 1 if x['status'] == STATUS_PARTIAL else 2, x['penalty']))
    return total_penalty, score, grade, findings


def interpretation(grade: str) -> str:
    return {
        'Healthy': 'The account demonstrates stable growth, controlled efficiency, and manageable risk exposure. Current trajectory supports continued scaling.',
        'Needs Attention': 'Performance gaps or efficiency pressures are emerging that may constrain scalability. Focused corrective action is recommended.',
        'At Risk': 'Structural performance deterioration or elevated risk indicators threaten business stability. Immediate intervention is required to restore trajectory.',
    }.get(grade, '')
