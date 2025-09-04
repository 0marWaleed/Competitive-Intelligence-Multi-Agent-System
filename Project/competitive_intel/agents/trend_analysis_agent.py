import os

_OrigTrendAgent = None
if os.environ.get("CI_USE_ORIGINAL_TRENDS") == "1":
    try:
        from trend_analysis_agent import MobileTrendAnalysisAgent as _OrigTrendAgent  # type: ignore
    except Exception:
        _OrigTrendAgent = None


class TrendAnalysisInterface:
    def __init__(self) -> None:
        self.agent = _OrigTrendAgent() if _OrigTrendAgent else None

    def analyze(self, classified_events: list[dict]) -> list:
        if not self.agent:
            # Simple fallback: aggregate counts by event_type and competitors
            from collections import Counter
            et_counts = Counter(ev.get('event_type','unknown') for ev in classified_events)
            comp_counts = Counter(ev.get('competitor','Unknown') for ev in classified_events)
            # Represent as plain dicts for UI
            insights = []
            if et_counts:
                top = et_counts.most_common(3)
                insights.append({'title': 'Event type distribution', 'type': 'summary', 'significance': 'Medium', 'confidence': 0.7, 'data': dict(et_counts)})
                insights.append({'title': 'Top event types', 'type': 'summary', 'significance': 'Medium', 'confidence': 0.7, 'data': dict(top)})
            if comp_counts:
                insights.append({'title': 'Most active competitors', 'type': 'summary', 'significance': 'Medium', 'confidence': 0.7, 'data': dict(comp_counts.most_common(5))})
            return insights
        return self.agent.analyze_mobile_trends(classified_events, time_window_days=120)


