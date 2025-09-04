from typing import Dict, Any
import os

_OrigClassifier = None
if os.environ.get("CI_USE_ORIGINAL_CLASSIFIER") == "1":
    try:
        from event_classification_agent import MobileCompanyEventClassifier as _OrigClassifier  # type: ignore
    except Exception:
        _OrigClassifier = None


class EventClassificationInterface:
    def __init__(self) -> None:
        self.classifier = _OrigClassifier() if _OrigClassifier else None

    def classify_items(self, items: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        outputs = []
        for it in items:
            # Normalize
            try:
                from competitive_intel.utils.common import normalize_event_dict
                norm = normalize_event_dict(it)
            except Exception:
                norm = it
            text = (norm.get('description') or f"{it.get('title','')}. {it.get('summary','') or it.get('description','')}").strip()
            if self.classifier:
                res = self.classifier.classify_event(text, {"source": norm.get("source", ""), "link": it.get("link", "")})
                entities = res.extracted_entities or {}
                if not entities.get('companies') and norm.get('competitor'):
                    entities['companies'] = [norm.get('competitor')]
                if not entities.get('locations') and norm.get('region'):
                    entities['locations'] = [norm.get('region')]
                metadata = res.metadata or {}
                if 'source' not in metadata and norm.get('source'):
                    metadata['source'] = norm.get('source')
                outputs.append({
                    "event_type": res.event_type.value,
                    "confidence": res.confidence_score,
                    "reasoning": res.reasoning,
                    "entities": entities,
                    "metadata": metadata,
                    "competitor": norm.get("competitor"),
                    "description": norm.get("description") or text,
                    "date": norm.get("date"),
                    "source": norm.get("source"),
                })
            else:
                t = text.lower()
                if any(k in t for k in ["launch", "unveil", "announce", "debut", "pre-order", "preorder", "flagship", "available", "preorder"]):
                    ev = "product_launch"
                elif any(k in t for k in ["price", "discount", "deal", "offer", "% off", "reduce", "cut"]):
                    ev = "pricing_change"
                elif any(k in t for k in ["campaign", "advert", "marketing", "influencer", "promotion"]):
                    ev = "marketing_campaign"
                elif any(k in t for k in ["expand", "enter market", "opening", "launch in", "store", "retail"]):
                    ev = "expansion"
                else:
                    ev = "unknown"
                outputs.append({
                    "event_type": ev,
                    "confidence": 0.5,
                    "reasoning": "Rule-based fallback classification.",
                    "entities": {
                        'companies': [norm.get('competitor')] if norm.get('competitor') else [],
                        'locations': [norm.get('region')] if norm.get('region') else []
                    },
                    "metadata": {
                        'source': norm.get('source'),
                        'id': norm.get('id')
                    },
                    "competitor": norm.get("competitor"),
                    "description": norm.get("description") or text,
                    "date": norm.get("date"),
                    "source": norm.get("source"),
                })
        return outputs


