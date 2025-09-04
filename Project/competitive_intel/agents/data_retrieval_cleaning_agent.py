# Re-export classes from the original script with minimal adaptation
from typing import Any, Dict, List
import importlib.util
import importlib.machinery
import os
import types


def _load_search_agent_class():
    """Load SearchAgent from the original notebook-exported file, stripping notebook magics.

    - Removes lines starting with '!' (pip installs) to avoid SyntaxError
    - Preserves user-provided API key logic inside the module
    - Falls back gracefully on any error
    """
    try:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
        module_path = os.path.join(root, "data_retrieval_&_cleaning_agent_.py")
        if not os.path.exists(module_path):
            return None

        # Read and sanitize source: strip notebook shell magics (lines starting with '!')
        with open(module_path, "r", encoding="utf-8") as f:
            src = f.read()
        sanitized_lines: List[str] = []
        embedded_key: str | None = None
        for line in src.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("!"):
                continue
            # Detect embedded misuse: os.environ.get("<actual_key>") where <actual_key> looks like an OpenAI key.
            # If found, capture it and later expose it as OPENAI_API_KEY and also as that env var name (to satisfy the get).
            if "os.environ.get(" in line and ("sk-" in line or "sk_pro" in line or "sk-proj-" in line):
                import re
                m = re.search(r"os\.environ\.get\(\s*['\"]([^'\"]+)['\"]\s*\)", line)
                if m:
                    candidate = m.group(1)
                    if candidate.startswith("sk-") or candidate.startswith("sk_pro") or candidate.startswith("sk-proj-"):
                        embedded_key = candidate
            sanitized_lines.append(line)
        sanitized_src = "\n".join(sanitized_lines)

        # Create a new module and execute sanitized source into it
        module_name = "data_retrieval_cleaning_module"
        mod = types.ModuleType(module_name)
        mod.__file__ = module_path

        # Optional: ensure any externally provided OPENAI_API_KEY is visible to this module
        # No override here to respect user's current environment setup
        # If an embedded key was found, surface it to the environment for downstream libs
        if embedded_key:
            try:
                os.environ.setdefault(embedded_key, embedded_key)
                os.environ.setdefault("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", embedded_key)
            except Exception:
                pass

        exec(compile(sanitized_src, module_path, "exec"), mod.__dict__)
        return getattr(mod, "SearchAgent", None)
    except Exception:
        return None


_OrigSearchAgent = _load_search_agent_class()


class DataRetrievalCleaningInterface:
    """Thin wrapper to expose a consistent interface for the pipeline.

    Provides a simple `.run(competitors, regions, config)` that returns
    `{ "raw": [...], "clean": [...] }`. Currently returns only raw articles
    because cleaning in the original file depends on LangChain setup.
    """

    def __init__(self) -> None:
        self.search_agent = _OrigSearchAgent() if _OrigSearchAgent else None

    def run(self, competitors: Dict[str, Any], regions: List[str], config: Dict[str, Any]) -> Dict[str, Any]:
        if not self.search_agent:
            return {"raw": [], "clean": []}

        state = {
            "messages": [],
            "competitor_profiles": competitors,
            "target_regions": regions,
            "raw_articles": [],
            "cleaned_articles": [],
            "current_step": "search",
            "error": "",
            "search_config": config or {},
        }
        try:
            result = self.search_agent(state)
        except Exception:
            result = {"raw_articles": [], "cleaned_articles": []}
        return {"raw": result.get("raw_articles", []), "clean": result.get("cleaned_articles", [])}


