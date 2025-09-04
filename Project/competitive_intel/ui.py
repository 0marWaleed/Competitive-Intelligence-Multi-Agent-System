import asyncio
from typing import Any, Dict, List

import streamlit as st
import os, sys
import pandas as pd

# Ensure project root is on sys.path so absolute imports work when run via Streamlit
_this_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_this_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from competitive_intel.langgraph_pipeline import run_with_langgraph
from competitive_intel.agents.report_generator_agent import ReportGeneratorInterface

st.set_page_config(page_title="Competitive Intelligence Monitor", layout="wide")
rg = ReportGeneratorInterface()

# Custom CSS for a professional, readable theme and components
st.markdown(
    """
    <style>
        :root {
            --primary: #2563EB; /* refined blue */
            --text: #111827;
            --muted-text: #6B7280;
            --border: #E5E7EB;
            --bg-soft: #F9FAFB;
        }
        .section-title {
            font-weight: 700; font-size: 1.05rem; margin: 8px 0 6px 0;
            color: var(--text);
        }
        .kpi-box { border: 1px solid var(--border); border-radius: 10px; padding: 12px; background: var(--bg-soft); }
        .pill { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.8rem; border: 1px solid var(--border); background: #fff; color: var(--text); }
        .pill-blue { border-color: #BFDBFE; color: #1D4ED8; }
        .pill-green { border-color: #BBF7D0; color: #047857; }
        .pill-amber { border-color: #FDE68A; color: #B45309; }
        .pill-red { border-color: #FCA5A5; color: #B91C1C; }
        .reco-card { border: 1px solid var(--border); border-radius: 12px; padding: 14px; margin-bottom: 12px; background: #ffffff; }
        .reco-title { font-weight: 600; font-size: 1rem; margin-bottom: 4px; color: var(--text); }
        .reco-meta { color: var(--muted-text); font-size: 0.9rem; margin-bottom: 8px; }
        .reco-steps { margin: 6px 0 0 0; }
        .reco-steps li { margin-left: 18px; }
        .company-chips span { margin-right: 6px; }
        .stTabs [data-baseweb="tab"] { font-weight: 600; }
        .dataframe tbody tr:hover { background: #F3F4F6; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.header("Settings")

# Options
COMPETITOR_OPTIONS = ["Apple","Samsung","Xiaomi","OPPO","vivo","Huawei","Google","OnePlus","Nothing"]
REGION_OPTIONS = ["US","EU","KSA","UAE","IN","EG","CN"]

select_all_comp = st.sidebar.checkbox("Select all competitors", value=True)
competitors_selected = st.sidebar.multiselect(
    "Competitors",
    options=COMPETITOR_OPTIONS,
    default=COMPETITOR_OPTIONS if select_all_comp else ["Apple","Samsung","Xiaomi","OPPO","vivo","Huawei"],
)

select_all_regions = st.sidebar.checkbox("Select all regions", value=True)
regions_selected = st.sidebar.multiselect(
    "Regions",
    options=REGION_OPTIONS,
    default=REGION_OPTIONS if select_all_regions else ["US","EU","KSA","UAE","IN"],
)

timeframe_days = st.sidebar.slider("Timeframe (days)", 1, 30, 7)
max_articles = st.sidebar.slider("Max articles per company", 5, 50, 15)
recommendation_focus = st.sidebar.text_area("Recommendation focus (optional)", placeholder="e.g., Emphasize quick wins for EMEA, budget-sensitive tactics, partnerships", height=80)
run_btn = st.sidebar.button("Run Pipeline")

st.title("Competitive Intelligence Monitor & Strategist")
st.caption("Track competitors, analyze, and act – end-to-end")

# Top KPIs
if 'data_cache' not in st.session_state:
    st.session_state['data_cache'] = None

placeholder = st.empty()

def run_pipeline() -> Dict[str, Any]:
    competitors = {name: {} for name in competitors_selected}
    regions = regions_selected
    config = {"search_timeframe_days": timeframe_days, "max_articles_per_company": max_articles, "use_langgraph": True}
    if recommendation_focus:
        config["recommendation_focus"] = recommendation_focus
    company_profile = {
        'size': 'Medium',
        'market_position': 'Value midrange challenger',
        'strengths': ['camera_quality', 'battery_life', 'after_sales_service'],
        'resources': 'Medium',
        'markets': regions,
    }
    return run_with_langgraph(competitors, regions, config, company_profile)


def render_dashboard(data: Dict[str, Any]) -> None:
    # Tabbed UI
    tab_overview, tab_trends, tab_impact, tab_strategy, tab_actions, tab_report = st.tabs([
        "Overview", "Trends", "Impact", "Strategy", "Actions", "Report"
    ])

    with tab_overview:
        st.markdown("<div class='section-title'>Latest Events (classified)</div>", unsafe_allow_html=True)
        st.dataframe(data.get('classified', []), use_container_width=True)

    with tab_trends:
        st.markdown("<div class='section-title'>Trends</div>", unsafe_allow_html=True)
        trends = data.get('trends', [])
        if trends:
            try:
                if trends and hasattr(trends[0], 'title'):
                    trends_df = pd.DataFrame([{
                        'title': t.title,
                        'type': t.trend_type.value,
                        'significance': t.significance.value,
                        'confidence': t.confidence_score,
                    } for t in trends])
                    st.dataframe(trends_df, use_container_width=True)
                else:
                    rows = []
                    for item in trends:
                        base = {
                            'title': item.get('title',''),
                            'type': item.get('type',''),
                            'significance': item.get('significance',''),
                            'confidence': item.get('confidence','')
                        }
                        if isinstance(item.get('data'), dict):
                            base['data'] = ', '.join(f"{k}:{v}" for k,v in item['data'].items())
                        rows.append(base)
                    if rows:
                        st.dataframe(pd.DataFrame(rows), use_container_width=True)
            except Exception:
                st.write("Trends available (objects)")

    with tab_impact:
        st.markdown("<div class='section-title'>Impact Scoring</div>", unsafe_allow_html=True)
        st.dataframe(data.get('scored', []), use_container_width=True)

    with tab_strategy:
        st.markdown("<div class='section-title'>Strategic Analysis</div>", unsafe_allow_html=True)
        agg = data.get('aggregated') or {}
        if agg.get('strategy_overview'):
            st.markdown(f"<div class='reco-card'><div class='reco-title'>Aggregated Strategy Overview</div><div class='reco-meta'>{agg.get('strategy_overview')}</div></div>", unsafe_allow_html=True)
        # Detailed plan
        plan = (agg or {}).get('detailed_plan') or {}
        if plan:
            st.markdown("<div class='section-title'>Executive Summary</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='reco-card'>{plan.get('executive_summary','')}</div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("<div class='section-title'>Strategic Pillars</div>", unsafe_allow_html=True)
                for p in plan.get('strategic_pillars', [])[:6]:
                    st.markdown(f"- {p}")
            with c2:
                st.markdown("<div class='section-title'>Key Threats</div>", unsafe_allow_html=True)
                for t in plan.get('threats', [])[:6]:
                    st.markdown(f"- {t}")
            st.markdown("<div class='section-title'>30/60/90 Day Plan</div>", unsafe_allow_html=True)
            ph1, ph2, ph3 = st.columns(3)
            with ph1:
                st.markdown("**30 Days**")
                for s in plan.get('thirty_sixty_ninety',{}).get('30_days',[]):
                    st.markdown(f"- {s}")
            with ph2:
                st.markdown("**60 Days**")
                for s in plan.get('thirty_sixty_ninety',{}).get('60_days',[]):
                    st.markdown(f"- {s}")
            with ph3:
                st.markdown("**90 Days**")
                for s in plan.get('thirty_sixty_ninety',{}).get('90_days',[]):
                    st.markdown(f"- {s}")
            st.markdown("<div class='section-title'>Counter-moves, Risks & KPIs</div>", unsafe_allow_html=True)
            rcol, kcol = st.columns(2)
            with rcol:
                for cm in plan.get('counter_moves', [])[:6]:
                    st.markdown(f"- {cm}")
                st.markdown("**Risks**")
                for r in plan.get('risks', [])[:6]:
                    st.markdown(f"- {r}")
            with kcol:
                st.markdown("**KPIs**")
                for k in plan.get('kpis', [])[:8]:
                    st.markdown(f"- {k}")
        for ev in data.get('strategic', [])[:6]:
            st.markdown(f"<div class='reco-card'><div class='reco-title'>{ev.get('competitor','')} – {ev.get('event_type','')}</div><div class='reco-meta'>{(ev.get('strategic') or {}).get('strategic_context', '')}</div></div>", unsafe_allow_html=True)

    with tab_actions:
        st.markdown("<div class='section-title'>Action Recommendations</div>", unsafe_allow_html=True)
        final_events = data.get('final', [])
        agg = data.get('aggregated') or {}
        top_actions = agg.get('top_actions') or []
        gen_action = (agg or {}).get('general_action')
        if gen_action:
            st.markdown("<div class='section-title'>General Action Recommendation</div>", unsafe_allow_html=True)
            r = gen_action
            priority = str(r.get('priority','')).lower()
            if 'critical' in priority or 'p0' in priority:
                pill = 'pill-red'
            elif 'high' in priority or 'p1' in priority:
                pill = 'pill-amber'
            elif 'medium' in priority or 'p2' in priority:
                pill = 'pill-blue'
            else:
                pill = 'pill-green'
            header = f"<span class='pill {pill}'>{r.get('priority','')}</span> <span class='reco-title'>{r.get('title','')}</span>"
            meta = f"<div class='reco-meta'>Urgency: {r.get('urgency_hours','')}h</div>"
            desc = r.get('description') or ''
            steps = r.get('implementation_steps') or []
            metrics = r.get('success_metrics') or []
            risks = r.get('risks') or []
            steps_html = "".join([f"<li>{s}</li>" for s in steps])
            metrics_html = "".join([f"<li>{m}</li>" for m in metrics])
            risks_html = "".join([f"<li>{x}</li>" for x in risks])
            body = ""
            if desc:
                body += f"<div style='margin:6px 0 6px 0'>{desc}</div>"
            if steps_html:
                body += f"<div class='reco-meta'>Steps</div><ul class='reco-steps'>{steps_html}</ul>"
            if metrics_html:
                body += f"<div class='reco-meta' style='margin-top:6px'>Success Metrics</div><ul class='reco-steps'>{metrics_html}</ul>"
            if risks_html:
                body += f"<div class='reco-meta' style='margin-top:6px'>Risks</div><ul class='reco-steps'>{risks_html}</ul>"
            st.markdown(f"<div class='reco-card'>{header}{meta}{body}</div>", unsafe_allow_html=True)

        if top_actions:
            st.markdown("<div class='section-title'>Top Actions (Aggregated)</div>", unsafe_allow_html=True)
            for r in top_actions[:8]:
                priority = str(r.get('priority','')).lower()
                if 'critical' in priority or 'p0' in priority:
                    pill = 'pill-red'
                elif 'high' in priority or 'p1' in priority:
                    pill = 'pill-amber'
                elif 'medium' in priority or 'p2' in priority:
                    pill = 'pill-blue'
                else:
                    pill = 'pill-green'
                title = r.get('title','')
                urgency = r.get('urgency_hours')
                header = f"<span class='pill {pill}'>{r.get('priority','')}</span> <span class='reco-title'>{title}</span>"
                meta = f"<div class='reco-meta'>Urgency: {urgency}h</div>"
                desc = r.get('description') or ''
                steps = r.get('implementation_steps') or []
                metrics = r.get('success_metrics') or []
                risks = r.get('risks') or []
                steps_html = "".join([f"<li>{s}</li>" for s in steps])
                metrics_html = "".join([f"<li>{m}</li>" for m in metrics])
                risks_html = "".join([f"<li>{x}</li>" for x in risks])
                body = ""
                if desc:
                    body += f"<div style='margin:6px 0 6px 0'>{desc}</div>"
                if steps_html:
                    body += f"<div class='reco-meta'>Steps</div><ul class='reco-steps'>{steps_html}</ul>"
                if metrics_html:
                    body += f"<div class='reco-meta' style='margin-top:6px'>Success Metrics</div><ul class='reco-steps'>{metrics_html}</ul>"
                if risks_html:
                    body += f"<div class='reco-meta' style='margin-top:6px'>Risks</div><ul class='reco-steps'>{risks_html}</ul>"
                st.markdown(f"<div class='reco-card'>{header}{meta}{body}</div>", unsafe_allow_html=True)
        total_rendered = 0
        for ev in final_events[:8]:
            recs = ev.get('actions', [])
            for r in recs:
                priority = str(r.get('priority','')).lower()
                if 'critical' in priority or 'p0' in priority:
                    pill = 'pill-red'
                elif 'high' in priority or 'p1' in priority:
                    pill = 'pill-amber'
                elif 'medium' in priority or 'p2' in priority:
                    pill = 'pill-blue'
                else:
                    pill = 'pill-green'
                title = r.get('title','')
                urgency = r.get('urgency_hours')
                header = f"<span class='pill {pill}'>{r.get('priority','')}</span> <span class='reco-title'>{title}</span>"
                meta = f"<div class='reco-meta'>{ev.get('competitor','')} – {ev.get('event_type','')} | Urgency: {urgency}h</div>"
                steps = r.get('implementation_steps') or []
                steps_html = "".join([f"<li>{s}</li>" for s in steps])
                body = f"<ul class='reco-steps'>{steps_html}</ul>" if steps_html else ""
                st.markdown(f"<div class='reco-card'>{header}{meta}{body}</div>", unsafe_allow_html=True)
                total_rendered += 1
        if total_rendered == 0:
            st.info("No action recommendations available.")

        # Download all actions as PDF (always offer button)
        try:
            actions_pdf = rg.export_actions_pdf(final_events)
            st.download_button(label="Download All Actions (PDF)", data=actions_pdf, file_name="actions_recommendations.pdf", mime="application/pdf")
        except Exception as e:
            st.exception(e)

    with tab_report:
        st.markdown("<div class='section-title'>Downloadable Report</div>", unsafe_allow_html=True)
        daily = data.get('daily_report', {})
        summary = daily.get('summary', {})
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"<div class='kpi-box'><div>Total events</div><div class='section-title'>{summary.get('total_events',0)}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='kpi-box'><div>Today</div><div class='section-title'>{summary.get('today_events',0)}</div></div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='kpi-box'><div>Critical/High</div><div class='section-title'>{summary.get('critical_or_high',0)}</div></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Companies</div>", unsafe_allow_html=True)
        chips = " ".join([f"<span class='pill pill-blue'>{c}</span>" for c in summary.get('companies_mentioned', [])])
        st.markdown(f"<div class='company-chips'>{chips}</div>", unsafe_allow_html=True)

        try:
            # Provide combined Daily Brief + Strategy (exec summary) + Actions as a PDF
            final_events = data.get('final', [])
            # Pass aggregated plan via hidden key in daily dict
            daily_with_agg = dict(daily)
            daily_with_agg['_aggregated'] = data.get('aggregated', {})
            pdf_bytes = rg.export_full_pdf(daily_with_agg, final_events)
            st.download_button(label="Download Full Report (PDF)", data=pdf_bytes, file_name="full_report.pdf", mime="application/pdf")
        except Exception as e:
            st.exception(e)


if run_btn:
    try:
        with st.spinner("Running pipeline..."):
            data = run_pipeline()
            st.session_state['data_cache'] = data
        render_dashboard(data)
    except Exception as e:
        st.exception(e)
else:
    cached = st.session_state.get('data_cache')
    if cached:
        render_dashboard(cached)
    else:
        st.info("Configure options in the sidebar and click Run Pipeline.")


