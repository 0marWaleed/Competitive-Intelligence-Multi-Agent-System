from typing import Dict, Any, List
import os

_OrigRecommender = None
if os.environ.get("CI_USE_ORIGINAL_ACTIONS") == "1":
    try:
        from action_recommender_agent import ActionRecommenderAgent as _OrigRecommender  # type: ignore
        from action_recommender_agent import ActionRecommendation  # type: ignore
    except Exception:
        _OrigRecommender = None
        ActionRecommendation = None  # type: ignore


class ActionRecommenderInterface:
    def __init__(self) -> None:
        # Auto-enable original recommender if OPENAI_API_KEY is present
        import os as _os
        global _OrigRecommender
        if not _OrigRecommender and _os.environ.get("OPENAI_API_KEY"):
            try:
                from action_recommender_agent import ActionRecommenderAgent as _Loaded  # type: ignore
                _OrigRecommender = _Loaded
            except Exception:
                _OrigRecommender = None
        self.agent = _OrigRecommender() if _OrigRecommender else None

    def recommend(self, event: Dict[str, Any], impact: float, strategy_context: str, company_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.agent:
            # Heuristic actions fallback
            ev = (event.get('event_type') or 'event').replace('_',' ')
            comp = event.get('competitor','Competitor')
            focus_note = company_profile.get('recommendation_focus') or ""
            base = [
                {
                    'title': f'Counter-plan for {comp} {ev}',
                    'priority': 'High' if impact >= 7 else 'Medium',
                    'category': 'Immediate Response',
                    'urgency_hours': 72 if impact >= 7 else 168,
                    'description': 'Coordinate rapid response across product, pricing, and marketing.' + (f" Focus: {focus_note}" if focus_note else ""),
                    'expected_impact': 'Medium',
                    'confidence': 0.7,
                    'implementation_steps': [
                        'Complete feature/price gap analysis',
                        'Draft counter-messaging and launch PR plan',
                        'Align retail/operator promotions where feasible'
                    ],
                    'success_metrics': ['Share retention', 'Uplift in consideration', 'Promo ROI'],
                    'risks': ['Price erosion', 'Resource stretch']
                },
                {
                    'title': 'Partner offer acceleration',
                    'priority': 'Medium' if impact < 7 else 'High',
                    'category': 'Partnerships & Alliances',
                    'urgency_hours': 168,
                    'description': 'Negotiate short-term bundles with priority operators/retailers to protect visibility.' + (f" Focus: {focus_note}" if focus_note else ""),
                    'expected_impact': 'Medium',
                    'confidence': 0.65,
                    'implementation_steps': ['Identify partners', 'Draft offer structure', 'Launch co-marketing'],
                    'success_metrics': ['Sell-through uplift', 'Partner shelf share'],
                    'risks': ['Channel conflicts']
                },
                {
                    'title': 'Value messaging refresh',
                    'priority': 'Medium',
                    'category': 'Marketing & Communication',
                    'urgency_hours': 120,
                    'description': 'Update creatives to emphasize strengths (battery, camera, service).' + (f" Focus: {focus_note}" if focus_note else ""),
                    'expected_impact': 'Medium',
                    'confidence': 0.7,
                    'implementation_steps': ['Define claims', 'Produce creatives', 'Deploy across channels'],
                    'success_metrics': ['CTR/engagement', 'Preference lift'],
                    'risks': ['Message clutter']
                }
            ]
            return base
        recs = self.agent.analyze_and_recommend(event, impact, strategy_context, company_profile)
        out: List[Dict[str, Any]] = []
        for r in recs:
            out.append({
                'title': r.title,
                'priority': r.priority.value,
                'category': r.category.value,
                'urgency_hours': r.urgency_hours,
                'description': r.description,
                'expected_impact': r.expected_impact,
                'confidence': r.confidence_score,
                'implementation_steps': r.implementation_steps,
                'success_metrics': r.success_metrics,
                'risks': r.risks,
            })
        return out


