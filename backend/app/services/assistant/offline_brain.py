"""Offline assistant: keyword/intent matching over the same context tools as
the Claude mode. Guarantees the demo works with zero API keys / no internet."""

from sqlalchemy.orm import Session

from app.services.assistant import context_tools as tools


def suggestions() -> list[str]:
    return [
        "Which animals are under withdrawal?",
        "Any MRL violations this month?",
        "What is the most used antimicrobial?",
        "Which animals are at high MRL risk?",
        "Any fever alerts from sensors?",
        "How is our AMU stewardship doing?",
    ]


def _fmt_withdrawal(rows: list[dict]) -> str:
    if not rows:
        return "No animals are under withdrawal right now — all clear. ✅"
    lines = [f"{len(rows)} animal(s) currently under withdrawal:"]
    for r in rows[:10]:
        tissues = ", ".join(f"{t['tissue']} clear in {t['countdown']}" for t in r["tissues"])
        drugs = ", ".join(sorted({t.get("drug_name") or "?" for t in r["tissues"]}))
        lines.append(f"• {r['tag_id']} ({r['species']}): {tissues} — drug: {drugs}")
    return "\n".join(lines)


def _fmt_violations(violations: list[dict]) -> str:
    if not violations:
        return "No MRL violations recorded in this period. 👍"
    lines = [f"{len(violations)} violation(s) found:"]
    for v in violations[:10]:
        lines.append(
            f"• {v['animal_tag']}: {v['quantity']} {v['product']} sold on {v['occurred']}"
        )
    return "\n".join(lines)


def answer(db: Session, farm_ids: list[int] | None, message: str) -> str:
    q = message.lower()

    if any(k in q for k in ("withdrawal", "withholding", "clear when", "safe to sell")):
        return _fmt_withdrawal(tools.under_withdrawal(db, farm_ids))

    if "violation" in q or "illegal" in q or "residue fail" in q:
        days = 7 if ("week" in q or "today" in q) else 30
        return _fmt_violations(tools.recent_violations(db, farm_ids, days=days))

    if "most used" in q or "top drug" in q or "commonly used" in q:
        stats = tools.amu_stats(db, farm_ids)
        board = stats["leaderboard"]
        if not board:
            return "No treatments recorded yet."
        top = board[0]
        aware = ", ".join(
            f"{b['aware_class']}: {int(b['share'] * 100)}%" for b in stats["aware_breakdown"]
        )
        return (
            f"Most used: {top['drug_name']} ({top['drug_class']}, WHO AWaRe: "
            f"{top['aware_class']}) with {top['uses']} recorded courses.\n"
            f"AWaRe mix: {aware}. Watch/Reserve overuse drives resistance — prefer Access drugs."
        )

    if "stewardship" in q or "amu" in q or "usage" in q:
        s = tools.compliance_summary(db, farm_ids)
        share = s.get("supervised_share")
        supervised_txt = f"{share * 100:.0f}% vet-supervised" if share is not None else "no data"
        return (
            f"Last 30 days: {s.get('amu_30d', 0)} treatment courses across "
            f"{s.get('total_active_animals', 0)} active animals ({supervised_txt}). "
            f"Total historical violations: {s.get('violations_total', 0)}."
        )

    if any(k in q for k in ("risk", "predict", "watchlist", "danger")):
        ranked = tools.risk_watchlist(db, farm_ids)
        if not ranked:
            return "ML models not trained yet — run the seed script first."
        lines = ["Highest predicted MRL-violation risk (synthetic-data demo model):"]
        for r in ranked[:5]:
            lines.append(f"• {r['tag_id']}: risk {r['risk']:.2f} ({r['band']})")
        return "\n".join(lines)

    if any(k in q for k in ("fever", "temperature", "sensor", "iot", "collar")):
        alerts = [a for a in tools.open_alerts(db, farm_ids, limit=20)
                  if a["type"] == "SENSOR_ANOMALY"]
        if not alerts:
            return (
                "No fever anomalies detected by IoT collars in the current window. "
                "(Simulated sensor feed; threshold 39.3°C.)"
            )
        return "Sensor anomaly alerts:\n" + "\n".join(f"• {a['title']}" for a in alerts)

    if any(k in q for k in ("alert", "warning", "attention")):
        alerts = tools.open_alerts(db, farm_ids)
        if not alerts:
            return "No open alerts. Everything looks calm. ✅"
        return f"{len(alerts)} open alert(s):\n" + "\n".join(
            f"[{a['severity'].upper()}] {a['title']}" for a in alerts[:8]
        )

    # animal tag lookup e.g. "tell me about MUR-0017"
    for token in message.replace(",", " ").split():
        t = token.strip().upper()
        if "-" in t and any(c.isdigit() for c in t):
            hist = tools.animal_history(db, t, farm_ids)
            if hist:
                wd = "YES ⚠️" if hist["under_withdrawal_now"] else "no"
                last = hist["recent_treatments"][0] if hist["recent_treatments"] else None
                last_txt = (
                    f" Last treatment: {last['drug']} ({last['started']}, course {last['course_days']}d)."
                    if last else " No treatments on record."
                )
                return (
                    f"{hist['tag_id']} — {hist['species']} ({hist['breed']}), "
                    f"{hist['production_status']}. Under withdrawal now: {wd}.{last_txt} "
                    f"Historical violations: {len(hist['violations'])}."
                )
            return f"I couldn't find an animal tagged '{t}' that you have access to."

    if any(k in q for k in ("hello", "hi", "help", "what can you")):
        return (
            "I can answer questions about your livestock data:\n"
            + "\n".join(f"• {s}" for s in suggestions())
        )

    return (
        "I'm not sure how to answer that offline. Try one of:\n"
        + "\n".join(f"• {s}" for s in suggestions())
        + "\n(Set ANTHROPIC_API_KEY to unlock free-form Claude answers.)"
    )
