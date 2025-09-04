from typing import List, Dict, Any
from datetime import datetime

try:
    from report_generator_agent import MobileMarketReportGenerator as _OrigReportGen  # type: ignore
except Exception:
    _OrigReportGen = None


class ReportGeneratorInterface:
    def __init__(self) -> None:
        self.agent = _OrigReportGen() if _OrigReportGen else None

    def generate_daily(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self.agent:
            # Minimal transform: the original expects dataclasses; we will pass an empty list
            # and instead synthesize a summary from our events for display.
            brief = self.agent.generate_daily_brief([])
        else:
            brief = {"report_type": "Daily Brief"}

        # Build a lightweight summary from our event dicts for UI
        today = datetime.now().date()
        def _to_dt(x):
            if isinstance(x, datetime):
                return x
            if isinstance(x, str):
                try:
                    return datetime.fromisoformat(x.replace('Z',''))
                except Exception:
                    return datetime.now()
            return datetime.now()

        today_events = [e for e in events if _to_dt(e.get('date')).date() == today]
        critical = [e for e in events if str(e.get('urgency','')).lower() in ("immediate","critical","high")]

        brief.update({
            "date": today.isoformat(),
            "summary": {
                "total_events": len(events),
                "today_events": len(today_events),
                "critical_or_high": len(critical),
                "companies_mentioned": sorted(list({e.get('competitor','Unknown') for e in events}))
            },
            "critical_events": [
                {
                    "title": (e.get('description') or '')[:80],
                    "competitor": e.get('competitor','Unknown'),
                    "event_type": e.get('event_type','unknown'),
                    "impact": e.get('impact', 0.0),
                    "urgency": e.get('urgency','')
                }
                for e in critical[:10]
            ]
        })

        return brief

    def export_pdf(self, daily_brief: Dict[str, Any], filename: str = None) -> str | bytes:
        """Create a simple PDF from the daily brief without requiring the original agent."""
        try:
            from fpdf import FPDF
            has_pdf = True
        except Exception:
            has_pdf = False

        if not filename:
            filename = f"daily_brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        if has_pdf:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            # Use a core font to avoid missing font issues and sanitize text to latin-1
            pdf.set_font("Helvetica", style="B", size=16)
            def _sanitize(text: str) -> str:
                # Replace common unicode punctuation for consistency, then sanitize
                replacements = {
                    "–": "-",
                    "—": "-",
                    "•": "-",
                    "“": '"',
                    "”": '"',
                    "’": "'",
                }
                t = text or ""
                for k, v in replacements.items():
                    t = t.replace(k, v)
                return t.encode('latin-1', 'replace').decode('latin-1')
            def _wrap_unbreakable(text: str, max_len: int = 60) -> str:
                # Break very long unbreakable tokens to avoid FPDF width errors
                parts = []
                for token in (_sanitize(text) or "").split():
                    if len(token) > max_len:
                        chunks = [token[i:i+max_len] for i in range(0, len(token), max_len)]
                        parts.append(" ".join(chunks))
                    else:
                        parts.append(token)
                return " ".join(parts)
            def _hr():
                y = pdf.get_y() + 2
                pdf.set_draw_color(200, 200, 200)
                pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
                pdf.ln(4)

            pdf.cell(0, 10, _wrap_unbreakable("Competitive Intelligence - Daily Brief"), ln=True)
            _hr()
            pdf.set_font("Helvetica", size=11)

            def write_line(text: str):
                # Ensure we start at left margin and use explicit writable width
                pdf.set_x(pdf.l_margin)
                usable_w = pdf.w - pdf.l_margin - pdf.r_margin
                pdf.multi_cell(usable_w, 6, _wrap_unbreakable(text))

            write_line(f"Date: {daily_brief.get('date','')}")
            write_line("")
            summary = daily_brief.get('summary', {})
            pdf.set_font("Helvetica", style="B", size=12)
            write_line("Summary")
            pdf.set_font("Helvetica", size=11)
            for k in ["total_events","today_events","critical_or_high"]:
                if k in summary:
                    write_line(f"- {k.replace('_',' ').title()}: {summary[k]}")
            companies = summary.get('companies_mentioned', [])
            if companies:
                write_line(f"- Companies: {', '.join(companies)}")

            _hr()
            pdf.set_font("Helvetica", style="B", size=12)
            write_line("Critical/High Events")
            pdf.set_font("Helvetica", size=11)
            for ev in daily_brief.get('critical_events', [])[:10]:
                write_line(f"- [{ev.get('urgency','')}] {ev.get('competitor','')}: {ev.get('title','')}")

            try:
                out = pdf.output(dest='S')
                # fpdf2 may return str or bytearray depending on version; normalize to bytes
                if isinstance(out, str):
                    return out.encode('latin-1', 'replace')
                if isinstance(out, bytearray):
                    return bytes(out)
                return out
            except Exception:
                pass

        # Fallback plain-text bytes if PDF generation not available
        lines = ["Competitive Intelligence – Daily Brief", f"Date: {daily_brief.get('date','')}", ""]
        summary = daily_brief.get('summary', {})
        lines.append("Summary:")
        for k in ["total_events","today_events","critical_or_high"]:
            if k in summary:
                lines.append(f"- {k}: {summary[k]}")
        companies = summary.get('companies_mentioned', [])
        if companies:
            lines.append(f"- Companies: {', '.join(companies)}")
        lines.append("")
        lines.append("Critical/High Events:")
        for ev in daily_brief.get('critical_events', [])[:10]:
            lines.append(f"• [{ev.get('urgency','')}] {ev.get('competitor','')}: {ev.get('title','')}")
        return ("\n".join(lines)).encode('utf-8')

    def export_actions_pdf(self, final_events: List[Dict[str, Any]], filename: str = None) -> str | bytes:
        """Create a PDF listing all recommended actions across events."""
        try:
            from fpdf import FPDF
            has_pdf = True
        except Exception:
            has_pdf = False

        if not filename:
            filename = f"actions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        # Flatten actions
        flattened: List[Dict[str, Any]] = []
        for ev in final_events:
            for act in ev.get('actions', []) or []:
                flattened.append({
                    'competitor': ev.get('competitor',''),
                    'event_type': ev.get('event_type',''),
                    'priority': act.get('priority',''),
                    'title': act.get('title',''),
                    'urgency_hours': act.get('urgency_hours'),
                    'implementation_steps': act.get('implementation_steps') or []
                })

        if has_pdf:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Helvetica", style="B", size=16)
            def _s(text: str) -> str:
                return (text or "").encode('latin-1', 'replace').decode('latin-1')
            def _wrap(text: str, max_len: int = 60) -> str:
                parts = []
                for token in (_s(text) or "").split():
                    if len(token) > max_len:
                        chunks = [token[i:i+max_len] for i in range(0, len(token), max_len)]
                        parts.append(" ".join(chunks))
                    else:
                        parts.append(token)
                return " ".join(parts)

            pdf.cell(0, 10, _wrap("Action Recommendations"), ln=True)
            pdf.set_font("Helvetica", size=11)
            for item in flattened:
                header = f"[{item.get('priority','')}] {item.get('title','')}"
                meta = f"{item.get('competitor','')} – {item.get('event_type','')} | Urgency: {item.get('urgency_hours','')}h"
                pdf.set_x(pdf.l_margin)
                usable_w = pdf.w - pdf.l_margin - pdf.r_margin
                pdf.multi_cell(usable_w, 6, _wrap(header))
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(usable_w, 6, _wrap(meta))
                steps = item.get('implementation_steps') or []
                for step in steps:
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(usable_w, 6, _wrap(f" - {step}"))
                pdf.ln(2)

            try:
                out = pdf.output(dest='S')
                if isinstance(out, str):
                    return out.encode('latin-1', 'replace')
                if isinstance(out, bytearray):
                    return bytes(out)
                return out
            except Exception:
                pass

        # Fallback plain-text bytes
        lines = ["Action Recommendations", ""]
        for item in flattened:
            lines.append(f"[{item.get('priority','')}] {item.get('title','')}")
            lines.append(f"{item.get('competitor','')} – {item.get('event_type','')} | Urgency: {item.get('urgency_hours','')}h")
            for step in item.get('implementation_steps') or []:
                lines.append(f" - {step}")
            lines.append("")
        return ("\n".join(lines)).encode('utf-8')


    def export_full_pdf(self, daily_brief: Dict[str, Any], final_events: List[Dict[str, Any]], filename: str = None) -> str | bytes:
        """Combined daily brief + all actions in one professional PDF."""
        try:
            from fpdf import FPDF
            has_pdf = True
        except Exception:
            has_pdf = False

        if not filename:
            filename = f"full_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        # Prepare flattened actions
        actions: List[Dict[str, Any]] = []
        for ev in final_events or []:
            for act in ev.get('actions', []) or []:
                actions.append({
                    'competitor': ev.get('competitor',''),
                    'event_type': ev.get('event_type',''),
                    'priority': act.get('priority',''),
                    'title': act.get('title',''),
                    'urgency_hours': act.get('urgency_hours'),
                    'implementation_steps': act.get('implementation_steps') or []
                })

        # Read aggregated plan from daily_brief passthrough if present
        aggregated = daily_brief.get('_aggregated', {}) if isinstance(daily_brief, dict) else {}
        plan = aggregated.get('detailed_plan', {}) if isinstance(aggregated, dict) else {}
        general_action = aggregated.get('general_action', {}) if isinstance(aggregated, dict) else {}

        if has_pdf:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=18)
            pdf.add_page()

            # Helpers
            def _s(text: str) -> str:
                replacements = {"–": "-", "—": "-", "•": "-", "“": '"', "”": '"', "’": "'"}
                t = text or ""
                for k, v in replacements.items():
                    t = t.replace(k, v)
                return t.encode('latin-1', 'replace').decode('latin-1')

            def _wrap(text: str, max_len: int = 60) -> str:
                parts = []
                for token in (_s(text) or "").split():
                    if len(token) > max_len:
                        chunks = [token[i:i+max_len] for i in range(0, len(token), max_len)]
                        parts.append(" ".join(chunks))
                    else:
                        parts.append(token)
                return " ".join(parts)

            def _usable_w() -> float:
                return pdf.w - pdf.l_margin - pdf.r_margin

            def _mcell(text: str, h: int = 8, border: int = 0, fill: bool = False):
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(_usable_w(), h, _wrap(text), border=border, fill=fill)

            def _title_bar(title: str):
                pdf.set_fill_color(37, 99, 235)  # blue
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Helvetica", style="B", size=18)
                pdf.cell(0, 14, _s(title), ln=True, fill=True, align='C')
                pdf.ln(2)
                pdf.set_text_color(0, 0, 0)

            def _section(title: str):
                pdf.set_fill_color(249, 250, 251)  # soft gray
                pdf.set_draw_color(229, 231, 235)
                pdf.set_font("Helvetica", style="B", size=13)
                pdf.cell(0, 10, _s(title), ln=True, fill=True, align='C')
                pdf.ln(2)
                pdf.set_font("Helvetica", size=11)

            def _action_block(item):
                # Header line with light background
                pdf.set_fill_color(243, 244, 246)
                pdf.set_draw_color(229, 231, 235)
                pdf.set_font("Helvetica", style="B", size=11)
                _mcell(f"[{item.get('priority','')}] {item.get('title','')}", fill=True, border=1)
                pdf.set_font("Helvetica", size=10)
                _mcell(f"{item.get('competitor','')} - {item.get('event_type','')} | Urgency: {item.get('urgency_hours','')}h", border=1)
                for step in item.get('implementation_steps') or []:
                    _mcell(f" • {step}", border=1)
                pdf.ln(2)

            # Title
            _title_bar("Competitive Intelligence - Daily Brief & Actions")

            # Summary section (no tables; spaced lines)
            _section("Summary")
            summary = (daily_brief or {}).get('summary', {})
            _mcell(f"- Total Events: {summary.get('total_events', 0)}")
            pdf.ln(1)
            _mcell(f"- Today: {summary.get('today_events', 0)}")
            pdf.ln(1)
            _mcell(f"- Critical/High: {summary.get('critical_or_high', 0)}")
            pdf.ln(2)
            companies = summary.get('companies_mentioned', [])
            if companies:
                _mcell(f"- Companies: {', '.join(companies)}")
                pdf.ln(2)

            # Critical events
            _section("Critical/High Events")
            for ev in (daily_brief or {}).get('critical_events', [])[:10]:
                _mcell(f"- [{ev.get('urgency','')}] {ev.get('competitor','')}: {ev.get('title','')}")
            pdf.ln(2)

            # Strategy (first part)
            if plan:
                _section("Executive Summary")
                _mcell(plan.get('executive_summary',''))
                pdf.ln(2)

            # Actions
            _section("Action Recommendations")
            if general_action:
                _mcell(f"General Action: {general_action.get('title','')}")
                _mcell(f"- Priority: {general_action.get('priority','')} | Urgency: {general_action.get('urgency_hours','')}h")
                if general_action.get('description'):
                    _mcell(general_action['description'])
                for s in general_action.get('implementation_steps', []):
                    _mcell(f" - {s}")
                for m in general_action.get('success_metrics', []):
                    _mcell(f" ✓ {m}")
                pdf.ln(2)
            for item in actions:
                _action_block(item)
                pdf.ln(3)

            try:
                out = pdf.output(dest='S')
                if isinstance(out, str):
                    return out.encode('latin-1', 'replace')
                if isinstance(out, bytearray):
                    return bytes(out)
                return out
            except Exception:
                pass

        # Fallback plain-text
        lines = ["Competitive Intelligence - Daily Brief & Actions", ""]
        summary = (daily_brief or {}).get('summary', {})
        for k in ["total_events","today_events","critical_or_high"]:
            if k in summary:
                lines.append(f"- {k}: {summary[k]}")
        companies = summary.get('companies_mentioned', [])
        if companies:
            lines.append(f"- Companies: {', '.join(companies)}")
        lines.append("")
        lines.append("Critical/High Events:")
        for ev in (daily_brief or {}).get('critical_events', [])[:10]:
            lines.append(f"- [{ev.get('urgency','')}] {ev.get('competitor','')}: {ev.get('title','')}")
        lines.append("")
        if plan:
            lines.append("Executive Summary:")
            lines.append(plan.get('executive_summary',''))
            lines.append("")
        lines.append("Action Recommendations:")
        if general_action:
            lines.append(f"General Action: {general_action.get('title','')}")
            lines.append(f"- Priority: {general_action.get('priority','')} | Urgency: {general_action.get('urgency_hours','')}h")
            if general_action.get('description'):
                lines.append(general_action['description'])
            for s in general_action.get('implementation_steps', []):
                lines.append(f" - {s}")
            for m in general_action.get('success_metrics', []):
                lines.append(f" ✓ {m}")
        for item in actions:
            lines.append(f"[{item.get('priority','')}] {item.get('title','')}")
            lines.append(f"{item.get('competitor','')} - {item.get('event_type','')} | Urgency: {item.get('urgency_hours','')}h")
            for step in item.get('implementation_steps') or []:
                lines.append(f" - {step}")
            lines.append("")
        return ("\n".join(lines)).encode('utf-8')
