from typing import Dict, Any
import os

_OrigImpactScorer = None
default_mobile_competitors = lambda: {}

if os.environ.get("CI_USE_ORIGINAL_IMPACT") == "1":
    try:
        from impact_scoring_agent import ImpactScoringAgent as _OrigImpactScorer, default_mobile_competitors  # type: ignore
    except Exception:
        _OrigImpactScorer = None
        default_mobile_competitors = lambda: {}


class ImpactScoringInterface:
    def __init__(self) -> None:
        self.scorer = _OrigImpactScorer(default_mobile_competitors()) if _OrigImpactScorer else None

    def score_events(self, events: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        scored = []
        for idx, ev in enumerate(events, 1):
            # Normalize
            try:
                from competitive_intel.utils.common import normalize_event_dict
                nev = normalize_event_dict(ev)
            except Exception:
                nev = ev
            signal = {
                'id': nev.get('id') or f'E{idx:04d}',
                'competitor': nev.get('competitor') or (ev.get('entities', {}).get('companies', ['Unknown'])[0] if isinstance(ev.get('entities'), dict) else 'Unknown'),
                'event_type': nev.get('event_type', 'other'),
                'text': nev.get('description', ''),
                'timestamp': nev.get('date'),
            }
            if self.scorer:
                score = self.scorer.score_signal(signal)
                ev_out = {**ev, 'impact': score.final_score, 'urgency': score.urgency, 'impact_breakdown': {
                    'size': score.competitor_size_score,
                    'event': score.event_significance_score,
                    'timing': score.timing_score,
                }, 'impact_reasoning': score.reasoning}
            else:
                # Heuristic scoring by event_type and brand size cues
                et = (signal.get('event_type') or 'other').lower()
                base = 5.0
                if 'launch' in et: base = 7.5
                elif 'pricing' in et or 'price' in et: base = 7.0
                elif 'carrier' in et or 'operator' in signal.get('text',''): base = 6.8
                elif 'campaign' in et or 'marketing' in et: base = 6.0
                elif 'certification' in et: base = 5.5
                # Big brands boost
                comp = (signal.get('competitor') or '').lower()
                if comp in ('samsung','apple','huawei'): base += 1.0
                # Recency tweak not available here; keep medium timing
                final = max(0.0, min(10.0, base))
                urgency = 'immediate' if final >= 8.0 else 'high' if final >= 7.0 else 'medium' if final >= 5.0 else 'low'
                ev_out = {**ev, 'impact': round(final,1), 'urgency': urgency, 'impact_breakdown': {'size': final-1, 'event': final, 'timing': 6.0}, 'impact_reasoning': 'Heuristic fallback score'}
            scored.append(ev_out)
        return scored


