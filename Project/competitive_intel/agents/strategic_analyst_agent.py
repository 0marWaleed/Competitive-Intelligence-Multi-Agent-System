from typing import Dict, Any
import os

_OrigAnalyst = None
if os.environ.get("CI_USE_ORIGINAL_ANALYST") == "1":
    try:
        from strategic_analyst_agent import StrategicAnalystAgent as _OrigAnalyst  # type: ignore
    except Exception:
        _OrigAnalyst = None


class StrategicAnalystInterface:
    def __init__(self) -> None:
        # Auto-enable original analyst if OPENAI_API_KEY is present
        import os as _os
        global _OrigAnalyst
        if not _OrigAnalyst and _os.environ.get("OPENAI_API_KEY"):
            try:
                from strategic_analyst_agent import StrategicAnalystAgent as _Loaded  # type: ignore
                _OrigAnalyst = _Loaded
            except Exception:
                _OrigAnalyst = None
        self.agent = _OrigAnalyst() if _OrigAnalyst else None

    async def analyze(self, event: Dict[str, Any]) -> Dict[str, Any]:
        if not self.agent:
            # Fallback heuristic context
            ev = (event.get('event_type') or '').replace('_',' ')
            comp = event.get('competitor','a competitor')
            desc = (event.get('description') or '')[:140]
            context = f"{comp} {ev}: {desc}."
            recs = []
            ev_l = ev.lower()
            if 'product launch' in ev_l or 'launch' in ev_l:
                recs = [
                    "Run rapid feature/price gap analysis vs launched product",
                    "Align counter-marketing emphasizing unique strengths",
                    "Review near-term roadmap pulls for parity features"
                ]
                context += " Focus: feature parity, pricing sensitivity, launch wave timing."
            elif 'pricing' in ev_l:
                recs = [
                    "Assess price elasticity and margin impact for selective response",
                    "Deploy tactical promos with partners in affected regions",
                    "Strengthen value messaging to defend positioning"
                ]
                context += " Focus: defensive pricing plays and value communication."
            elif 'carrier' in ev_l or 'operator' in desc.lower():
                recs = [
                    "Engage priority operators for bundle negotiations",
                    "Create exclusive partner offers to counter visibility",
                    "Ensure channel inventory and training readiness"
                ]
                context += " Focus: operator relationships and bundles."
            elif 'marketing' in ev_l or 'campaign' in ev_l:
                recs = [
                    "Spin counter-messaging content with creators",
                    "Amplify strengths via paid/owned channels",
                    "Track lift and sentiment; iterate weekly"
                ]
            else:
                recs = [
                    "Validate relevance and track escalation criteria",
                    "Prepare lightweight response options",
                    "Monitor competitor chatter and consumer sentiment"
                ]
            return {
                'strategic_context': context,
                'recommendations': recs,
                'broader_trends': ["AI features race", "Pricing pressure in mid-range", "Operator bundle competition"],
                'competitive_implications': "Need to defend share through value messaging and selective promos"
            }
        analysis = await self.agent.analyze_signal({
            'id': event.get('id'),
            'competitor': event.get('competitor'),
            'event_type': event.get('event_type'),
            'text': event.get('description'),
            'impact_score': event.get('impact'),
            'source': event.get('source'),
            'timestamp': event.get('date'),
        })
        return {
            'strategic_context': analysis.strategic_context,
            'recommendations': analysis.strategic_recommendations,
            'broader_trends': analysis.broader_trends,
            'competitive_implications': analysis.competitive_implications,
        }


