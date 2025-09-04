from __future__ import annotations

from typing import Any, Dict, List

try:
    from langgraph.graph import StateGraph, END
except Exception:
    StateGraph = None  # type: ignore
    END = None  # type: ignore

from .agents.data_retrieval_cleaning_agent import DataRetrievalCleaningInterface
from .agents.event_classification_agent import EventClassificationInterface
from .agents.trend_analysis_agent import TrendAnalysisInterface
from .agents.impact_scoring_agent import ImpactScoringInterface
from .agents.strategic_analyst_agent import StrategicAnalystInterface
from .agents.action_recommender_agent import ActionRecommenderInterface
from .agents.report_generator_agent import ReportGeneratorInterface


def build_langgraph_pipeline() -> Any:
    if StateGraph is None:
        return None

    class State(dict):
        pass

    sg = StateGraph(State)

    # Helper to ensure agents are available in every node
    def _ensure_agents(state: State) -> Dict[str, Any]:
        agents = state.get('agents')
        if agents is None:
            agents = {
                'retrieve': DataRetrievalCleaningInterface(),
                'classify': EventClassificationInterface(),
                'trends': TrendAnalysisInterface(),
                'scorer': ImpactScoringInterface(),
                'analyst': StrategicAnalystInterface(),
                'actions': ActionRecommenderInterface(),
                'reports': ReportGeneratorInterface(),
            }
            state['agents'] = agents
        return agents

    # Nodes
    def n_retrieve(state: State) -> State:
        agents = _ensure_agents(state)
        data = agents['retrieve'].run(state.get('competitors', {}), state.get('regions', []), state.get('config', {}))
        raw_items = data.get('clean') or data.get('raw') or []
        # Fallback demo data if retrieval produced nothing (e.g., offline or missing deps)
        if not raw_items:
            from datetime import datetime, timedelta
            now = datetime.now()
            comp_list = list(state.get('competitors', {}).keys()) or [
                "Samsung","Apple","Xiaomi","OPPO","vivo","Huawei","Google","OnePlus","Nothing"
            ]
            reg_list = state.get('regions') or ["US","EU","KSA","UAE","IN"]
            cfg = state.get('config', {}) or {}
            max_items = int(cfg.get("max_articles_per_company", 10) or 10)
            days = int(cfg.get("search_timeframe_days", 7) or 7)
            templates = [
                ("product_launch", "launch", "announces new flagship with AI camera and 5G"),
                ("pricing_change", "pricing", "introduces price cuts across key models"),
                ("partnership", "partnership", "signs operator partnership in {region}"),
                ("marketing_campaign", "marketing", "launches regional marketing push focusing on camera"),
                ("expansion", "expansion", "expands retail footprint in {region}")
            ]
            raw_items = []
            idx = 0
            for comp in comp_list:
                for i in range(max_items):
                    region = reg_list[(idx + i) % len(reg_list)]
                    t = templates[(idx + i) % len(templates)]
                    age_hours = min(days*24 - 1, (idx + i) * 6)
                    if age_hours < 0:
                        age_hours = 0
                    title = f"{comp} {t[1].replace('_',' ')} in {region}"
                    summary = t[2].format(region=region)
                    raw_items.append({
                        'title': title,
                        'summary': summary,
                        'company': comp,
                        'region': region,
                        'published': (now - timedelta(hours=age_hours)).isoformat(),
                        'source': f"{comp} News",
                        'link': f"https://example.com/{comp.lower()}-{t[0]}-{region.lower()}"
                    })
                idx += 1
        state['raw'] = raw_items
        return state

    def n_classify(state: State) -> State:
        agents = _ensure_agents(state)
        state['classified'] = agents['classify'].classify_items(state.get('raw', []))
        for ev in state.get('classified', []):
            ev.setdefault('event_type', 'unknown')
            ev.setdefault('competitor', 'Unknown')
            ev.setdefault('description', '')
        return state

    def n_trends(state: State) -> State:
        agents = _ensure_agents(state)
        state['trends'] = agents['trends'].analyze(state.get('classified', []))
        return state

    def n_score(state: State) -> State:
        agents = _ensure_agents(state)
        # normalize dates
        from datetime import datetime
        for ev in state.get('classified', []):
            dt = ev.get('date')
            if isinstance(dt, str):
                try:
                    ev['date'] = datetime.fromisoformat(dt.replace('Z',''))
                except Exception:
                    ev['date'] = datetime.now()
            elif not isinstance(dt, datetime):
                ev['date'] = datetime.now()
        state['scored'] = agents['scorer'].score_events(state.get('classified', []))
        return state

    def n_analyze(state: State) -> State:
        agents = _ensure_agents(state)
        results: List[Dict[str, Any]] = []
        import asyncio
        for ev in state.get('scored', [])[:10]:
            analyze_func = agents['analyst'].analyze
            if asyncio.iscoroutinefunction(analyze_func):
                try:
                    strategic = asyncio.run(analyze_func(ev))
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    try:
                        strategic = loop.run_until_complete(analyze_func(ev))  # type: ignore[misc]
                    finally:
                        loop.close()
            else:
                strategic = analyze_func(ev)  # type: ignore[misc]
            results.append({**ev, 'strategic': strategic})
        state['strategic'] = results
        return state

    def n_actions(state: State) -> State:
        agents = _ensure_agents(state)
        out: List[Dict[str, Any]] = []
        aggregated_actions: List[Dict[str, Any]] = []
        for ev in state.get('strategic', []):
            recs = agents['actions'].recommend(
                {
                    'event_type': ev.get('event_type'),
                    'competitor': ev.get('competitor'),
                    'description': ev.get('description'),
                    'date': ev.get('date'),
                    'source': ev.get('source'),
                },
                ev.get('impact', 0.0),
                (ev.get('strategic') or {}).get('strategic_context', ''),
                state.get('company_profile', {}),
            )
            out.append({**ev, 'actions': recs})
            aggregated_actions.extend(recs)

        # Aggregate strategy
        combined_contexts = [(ev.get('strategic') or {}).get('strategic_context','') for ev in state.get('strategic', []) if (ev.get('strategic') or {}).get('strategic_context')]
        combined_context = ". ".join([c.strip().rstrip('.') for c in combined_contexts])

        def _summarize_threats(evts: List[Dict[str, Any]]) -> List[str]:
            out_th = []
            for e in evts:
                comp = e.get('competitor','')
                et   = e.get('event_type','')
                if 'pricing' in str(et).lower():
                    out_th.append(f"Pricing pressure from {comp}")
                if 'launch' in str(et).lower():
                    out_th.append(f"Flagship launch momentum by {comp}")
                if 'partnership' in str(et).lower() or 'operator' in (e.get('description','').lower()):
                    out_th.append(f"Operator/retail visibility shift toward {comp}")
            return list(dict.fromkeys(out_th))[:6]

        def _pillars() -> List[str]:
            return [
                "Defend value with selective promos and clear superiority claims",
                "Deepen operator/retail partnerships for end-cap and bundle visibility",
                "Accelerate camera/AI differentiators in next launch wave",
                "Strengthen after-sales and trade-in to reduce churn",
                "Double down on regional hero SKUs aligned to price bands",
            ]

        detailed_plan = {
            'executive_summary': (
                combined_context[:800]
                or (
                    "Competitive intensity remains elevated across launches, pricing, and channel visibility. "
                    "Our plan: (1) defend value where we win today, (2) over-invest in operator/retail presence to capture mindshare, and (3) accelerate camera/AI differentiation in the next wave. "
                    "Over 90 days, sequence counter-moves to convert demand at shelf, blunt price aggression without margin leakage, and communicate proof-points that matter by region."
                )
            ),
            'strategic_pillars': _pillars(),
            'threats': _summarize_threats(state.get('scored', [])),
        }

        general_action = {
            'title': 'Win the shelf and blunt price plays in 90 days',
            'priority': 'High',
            'urgency_hours': 720,
            'description': 'Sequence counter-moves to convert demand at shelf: targeted promos on hero SKUs, creator-led proofs vs launches, and fast-tracked operator bundles in two priority regions.',
            'implementation_steps': [
                'Lock operator/retail end-caps and co-op calendars in 2 regions',
                'Run camera/AI proof content with creators within 2 weeks',
                'Deploy tightly-scoped promos on budget/mid hero SKUs with ROI guardrails'
            ],
            'success_metrics': ['Sell-through uplift', 'Share-of-voice at shelf', 'Promo ROI > target'],
            'risks': ['Margin compression', 'Channel conflicts']
        }

        state['final'] = out
        state['aggregated'] = {
            'strategy_overview': combined_context[:1000],
            'top_actions': aggregated_actions[:20],
            'detailed_plan': detailed_plan,
            'general_action': general_action,
        }
        return state

    def n_report(state: State) -> State:
        agents = _ensure_agents(state)
        state['daily_report'] = agents['reports'].generate_daily(state.get('final', []))
        return state

    # Register nodes
    sg.add_node('retrieve', n_retrieve)
    sg.add_node('classify', n_classify)
    sg.add_node('trends', n_trends)
    sg.add_node('score', n_score)
    sg.add_node('analyze', n_analyze)
    sg.add_node('actions', n_actions)

    # Optional LLM aggregation for professional exec summary and general action
    def n_llm_aggregate(state: State) -> State:
        import os
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return state
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            # Build concise inputs
            events_text = []
            for ev in state.get('strategic', [])[:20]:
                comp = ev.get('competitor','')
                et = ev.get('event_type','')
                desc = (ev.get('description') or '')[:200]
                impact = ev.get('impact', 0)
                ctx = (ev.get('strategic') or {}).get('strategic_context','')[:300]
                events_text.append(f"- {comp} {et} (impact {impact}): {desc} | ctx: {ctx}")
            company = state.get('company_profile', {})
            focus = state.get('config', {}).get('recommendation_focus','')

            prompt = (
                "You are a senior strategy assistant for a smartphone OEM.\n"
                "Given these competitive signals, produce:\n"
                "1) Executive Summary (3-5 sentences, board-ready, directive, no fluff).\n"
                "2) One General Action Recommendation object with: title, priority (Critical/High/... ), urgency_hours, description, implementation_steps(3-6), success_metrics(3-5), risks(2-4).\n"
                "Return ONLY valid JSON with keys {\"executive_summary\": str, \"general_action\": { ... }}.\n\n"
                f"COMPANY CONTEXT: size={company.get('size','')}, position={company.get('market_position','')}, strengths={', '.join(company.get('strengths',[]))}, markets={', '.join(company.get('markets',[]))}\n"
                + (f"FOCUS: {focus}\n" if focus else "")
                + "EVENTS:\n" + "\n".join(events_text)
            )

            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "Return JSON only. Be specific and directive."},
                    {"role": "user", "content": prompt},
                ],
            )
            content = resp.choices[0].message.content or "{}"
            import json
            data = json.loads(content)
            aggregated = state.get('aggregated', {})
            if isinstance(data.get('executive_summary'), str):
                # attach to detailed_plan
                plan = aggregated.get('detailed_plan', {})
                plan['executive_summary'] = data['executive_summary']
                aggregated['detailed_plan'] = plan
            if isinstance(data.get('general_action'), dict):
                aggregated['general_action'] = data['general_action']
            state['aggregated'] = aggregated
            return state
        except Exception:
            return state

    sg.add_node('llm_aggregate', n_llm_aggregate)
    sg.add_node('report', n_report)

    # Edges
    sg.set_entry_point('retrieve')
    sg.add_edge('retrieve', 'classify')
    sg.add_edge('classify', 'trends')
    sg.add_edge('trends', 'score')
    sg.add_edge('score', 'analyze')
    sg.add_edge('analyze', 'actions')
    sg.add_edge('actions', 'llm_aggregate')
    sg.add_edge('llm_aggregate', 'report')
    sg.add_edge('report', END)

    return sg.compile()


def run_with_langgraph(competitors: Dict[str, Any], regions: List[str], config: Dict[str, Any], company_profile: Dict[str, Any]) -> Dict[str, Any]:
    graph = build_langgraph_pipeline()
    if graph is None:
        raise RuntimeError("LangGraph is not available. Please install langgraph>=0.2")
    agents = {
        'retrieve': DataRetrievalCleaningInterface(),
        'classify': EventClassificationInterface(),
        'trends': TrendAnalysisInterface(),
        'scorer': ImpactScoringInterface(),
        'analyst': StrategicAnalystInterface(),
        'actions': ActionRecommenderInterface(),
        'reports': ReportGeneratorInterface(),
    }
    state = {
        'agents': agents,
        'competitors': competitors,
        'regions': regions,
        'config': config,
        'company_profile': company_profile,
    }
    def _fallback_run() -> Dict[str, Any]:
        # Minimal synchronous fallback reproducing the classic pipeline behavior
        retrieve = DataRetrievalCleaningInterface()
        classify = EventClassificationInterface()
        trends = TrendAnalysisInterface()
        scorer = ImpactScoringInterface()
        analyst = StrategicAnalystInterface()
        actions = ActionRecommenderInterface()
        reports = ReportGeneratorInterface()

        fetched = retrieve.run(competitors, regions, config)
        raw_items = (fetched.get("clean") or fetched.get("raw") or [])
        if not raw_items:
            from datetime import datetime, timedelta
            now = datetime.now()
            comp_list = list(competitors.keys()) or ["Samsung","Apple","Xiaomi","OPPO","vivo","Huawei","Google","OnePlus","Nothing"]
            reg_list = regions or ["US","EU","KSA","UAE","IN"]
            max_items = int(config.get("max_articles_per_company", 10) or 10)
            days = int(config.get("search_timeframe_days", 7) or 7)
            templates = [
                ("product_launch", "launch", "announces new flagship with AI camera and 5G"),
                ("pricing_change", "pricing", "introduces price cuts across key models"),
                ("partnership", "partnership", "signs operator partnership in {region}"),
                ("marketing_campaign", "marketing", "launches regional marketing push focusing on camera"),
                ("expansion", "expansion", "expands retail footprint in {region}")
            ]
            raw_items = []
            idx = 0
            for comp in comp_list:
                for i in range(max_items):
                    region = reg_list[(idx + i) % len(reg_list)]
                    t = templates[(idx + i) % len(templates)]
                    age_hours = min(days*24 - 1, (idx + i) * 6)
                    if age_hours < 0: age_hours = 0
                    title = f"{comp} {t[1].replace('_',' ')} in {region}"
                    summary = t[2].format(region=region)
                    raw_items.append({
                        'title': title,
                        'summary': summary,
                        'company': comp,
                        'region': region,
                        'published': (now - timedelta(hours=age_hours)).isoformat(),
                        'source': f"{comp} News",
                        'link': f"https://example.com/{comp.lower()}-{t[0]}-{region.lower()}"
                    })
                idx += 1

        classified = classify.classify_items(raw_items)
        for ev in classified:
            ev.setdefault('event_type', 'unknown')
            ev.setdefault('competitor', 'Unknown')
            ev.setdefault('description', '')

        trend_insights = trends.analyze(classified)

        from datetime import datetime
        for ev in classified:
            dt = ev.get('date')
            if isinstance(dt, str):
                try:
                    ev['date'] = datetime.fromisoformat(dt.replace('Z',''))
                except Exception:
                    ev['date'] = datetime.now()
            elif not isinstance(dt, datetime):
                ev['date'] = datetime.now()

        scored = scorer.score_events(classified)

        # Run analyst synchronously
        strategic_results: List[Dict[str, Any]] = []
        for ev in scored[:10]:
            try:
                res = analyst.analyze(ev)
                # If coroutine, run immediately
                import asyncio
                if asyncio.iscoroutine(res):
                    try:
                        res = asyncio.run(res)
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        try:
                            res = loop.run_until_complete(res)
                        finally:
                            loop.close()
                strategic = res
            except Exception:
                strategic = {'strategic_context': '', 'recommendations': [], 'broader_trends': [], 'competitive_implications': ''}
            strategic_results.append({**ev, 'strategic': strategic})

        final_with_actions: List[Dict[str, Any]] = []
        aggregated_actions: List[Dict[str, Any]] = []
        for ev in strategic_results:
            recs = actions.recommend(
                {
                    'event_type': ev.get('event_type'),
                    'competitor': ev.get('competitor'),
                    'description': ev.get('description'),
                    'date': ev.get('date'),
                    'source': ev.get('source'),
                },
                ev.get('impact', 0.0),
                (ev.get('strategic') or {}).get('strategic_context', ''),
                company_profile,
            )
            final_with_actions.append({**ev, 'actions': recs})
            aggregated_actions.extend(recs)

        combined_contexts = [(ev.get('strategic') or {}).get('strategic_context','') for ev in strategic_results if (ev.get('strategic') or {}).get('strategic_context')]
        combined_context = ". ".join([c.strip().rstrip('.') for c in combined_contexts])
        detailed_plan = {
            'executive_summary': combined_context[:800] or "",
            'strategic_pillars': [
                "Defend value with selective promos and clear superiority claims",
                "Deepen operator/retail partnerships for end-cap and bundle visibility",
                "Accelerate camera/AI differentiators in next launch wave",
                "Strengthen after-sales and trade-in to reduce churn",
                "Double down on regional hero SKUs aligned to price bands",
            ],
            'threats': [t for t in (
                (f"Pricing pressure from {ev.get('competitor','')}") if 'pricing' in str(ev.get('event_type','')).lower() else None,
                (f"Flagship launch momentum by {ev.get('competitor','')}") if 'launch' in str(ev.get('event_type','')).lower() else None,
                (f"Operator/retail visibility shift toward {ev.get('competitor','')}") if ('partnership' in str(ev.get('event_type','')).lower() or 'operator' in (ev.get('description','').lower())) else None,
            ) if t]
        }
        aggregated = {
            'strategy_overview': combined_context[:1000],
            'top_actions': aggregated_actions[:20],
            'detailed_plan': detailed_plan,
            'general_action': {
                'title': 'Win the shelf and blunt price plays in 90 days',
                'priority': 'High',
                'urgency_hours': 720,
                'description': 'Sequence counter-moves to convert demand at shelf: targeted promos on hero SKUs, creator-led proofs vs launches, and fast-tracked operator bundles in two priority regions.',
                'implementation_steps': [
                    'Lock operator/retail end-caps and co-op calendars in 2 regions',
                    'Run camera/AI proof content with creators within 2 weeks',
                    'Deploy tightly-scoped promos on budget/mid hero SKUs with ROI guardrails'
                ],
                'success_metrics': ['Sell-through uplift', 'Share-of-voice at shelf', 'Promo ROI > target'],
                'risks': ['Margin compression', 'Channel conflicts']
            }
        }
        daily = reports.generate_daily(final_with_actions)
        return {
            'raw': raw_items,
            'classified': classified,
            'trends': trend_insights,
            'scored': scored,
            'strategic': strategic_results,
            'final': final_with_actions,
            'aggregated': aggregated,
            'daily_report': daily,
        }

    result = graph.invoke(state)
    if not isinstance(result, dict) or result is None:
        result = state
    out = {
        'raw': result.get('raw', []),
        'classified': result.get('classified', []),
        'trends': result.get('trends', []),
        'scored': result.get('scored', []),
        'strategic': result.get('strategic', []),
        'final': result.get('final', []),
        'aggregated': result.get('aggregated', {}),
        'daily_report': result.get('daily_report', {}),
    }
    # If graph produced nothing, run the synchronous fallback
    if not out['raw'] and not out['classified'] and not out['final']:
        return _fallback_run()
    return out


