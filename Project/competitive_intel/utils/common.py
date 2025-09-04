from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


def coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z',''))
        except Exception:
            return datetime.now()
    return datetime.now()


def normalize_event_dict(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map heterogeneous keys to a common structure used across agents."""
    comp = raw.get('competitor') or raw.get('company') or raw.get('brand') or 'Unknown'
    comp_map = {
        'oppo': 'OPPO',
        'vivo': 'vivo',
        'xiami': 'Xiaomi',
        'xiaomi': 'Xiaomi',
        'samsung': 'Samsung',
        'apple': 'Apple',
        'huawei': 'Huawei',
        'oneplus': 'OnePlus',
        'nothing': 'Nothing',
        'google': 'Google'
    }
    comp_canon = comp_map.get(str(comp).lower(), comp)
    return {
        'id': raw.get('id') or raw.get('event_id') or raw.get('link') or raw.get('title'),
        'competitor': comp_canon,
        'event_type': raw.get('event_type') or raw.get('content_type') or 'unknown',
        'description': raw.get('description') or raw.get('summary') or raw.get('raw_text') or raw.get('title') or '',
        'date': coerce_datetime(raw.get('date') or raw.get('published') or raw.get('timestamp')),
        'source': raw.get('source') or raw.get('source_url') or raw.get('link') or '',
        'region': raw.get('region') or '',
    }


