#!/usr/bin/env python3
"""Parse AMF Art. 223-16 share/voting-rights declaration PDFs (downloaded by
fetch_capital.mjs) and merge the share-capital history into
pipeline/state/share_capital.json.

Policy: the latest AMF declaration always wins over the seeded spreadsheet
values, UNLESS the state entry carries "manual": true — then only the history
array is updated and the pinned total/date is left alone.
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

MONTHS = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "decembre": 12,
}

NUM_RE = re.compile(r"\d{1,3}(?:[ .]\d{3})+|\d{4,}")
DATE_FR_RE = re.compile(r"(\d{1,2})(?:er)?\s+(janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre)\s+(\d{4})")
DATE_NUM_RE = re.compile(r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})")

# "Societe anonyme au capital de 4.620.044,74 euros" is the share capital in
# EUROS, not the number of shares; strip it before looking for share counts.
CAPITAL_IN_EUROS_RE = re.compile(
    r"capital(?:\s+social)?\s*(?:de|:)?\s*\d[\d .,]*\s*(?:euros?\b|eur\b|\u20ac)"
)

# Company registration numbers ("316 580 869 R.C.S. Paris", "RCS Nanterre
# 562 018 002", "SIREN 390 474 898") look like share counts; strip them too.
REGISTRATION_RE = re.compile(
    r"\d{3}[ .]?\d{3}[ .]?\d{3}\s*(?:r\.?\s*c\.?\s*s\b\.?|rcs\b)"
    r"|(?:r\.?\s*c\.?\s*s\b\.?|rcs\b|siren|siret)\s*(?:[a-z'-]+\s*){0,3}:?\s*\d{3}[ .]?\d{3}[ .]?\d{3}(?:[ .]?\d{5})?"
)

ANCHORS = [
    "actions composant le capital",
    "nombre total d'actions",
    "nombre total d actions",
    "actions composing the share capital",
    "total number of shares",
    "nombre d'actions",
    "nombre d actions",
]


def strip_accents(text):
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text) if not unicodedata.combining(ch)
    )


def normalise_target_key(value):
    text = strip_accents(str(value or "")).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(
        r"\b(SOCIETE ANONYME FRANCAISE|SOCIETE ANONYME|SOCIETE|ANONYME|FRANCAISE|"
        r"SA|SAS|SCA|SE|PLC|LTD|NV|SPA|AG|AB)\b",
        " ",
        text,
    )
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_number(token):
    return int(re.sub(r"[ .]", "", token))


def find_as_at_date(chunk):
    m = DATE_FR_RE.search(chunk)
    if m:
        month = MONTHS.get(m.group(2))
        if month:
            return f"{int(m.group(3)):04d}-{month:02d}-{int(m.group(1)):02d}"
    m = DATE_NUM_RE.search(chunk)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31 and 1990 < year < 2100:
            return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def parse_pdf(path):
    try:
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:  # noqa: BLE001
        return {"error": f"pdf read failed: {error}"}
    text = text.replace(" ", " ").replace(" ", " ").replace("’", "'")
    plain = strip_accents(text.lower())
    plain = CAPITAL_IN_EUROS_RE.sub(" ", plain)
    plain = REGISTRATION_RE.sub(" ", plain)

    # The anchor phrase usually appears both in the title and in the table
    # header; the table (with the actual figures) comes later, so try anchor
    # positions from last to first and keep the first window with numbers.
    positions = []
    for phrase in ANCHORS:
        start = 0
        while True:
            found = plain.find(phrase, start)
            if found < 0:
                break
            positions.append(found)
            start = found + 1
        if positions:
            break
    candidates = sorted(set(positions), reverse=True) or [None]

    def numbers_in(chunk):
        found = []
        chunk = DATE_NUM_RE.sub(" ", chunk)  # "31.08.2026" is not "08.202"
        for m in NUM_RE.finditer(chunk):
            value = parse_number(m.group())
            if value >= 5000:  # skips years, article numbers, small figures
                found.append(value)
        return found

    for anchor in candidates:
        if anchor is None:
            window = plain[:2500]
            after_anchor = window
        else:
            window = plain[max(0, anchor - 200):anchor + 800]
            after_anchor = plain[anchor:anchor + 800]
        # Prefer figures after the anchor (the table), so postcodes and other
        # header numbers just before it are not mistaken for the share count.
        numbers = numbers_in(after_anchor) or numbers_in(window)
        if numbers:
            return {
                "shares": numbers[0],
                "votes": numbers[1] if len(numbers) > 1 else None,
                "as_at": find_as_at_date(after_anchor) or find_as_at_date(window),
                "anchor_found": anchor is not None,
            }
    return {"error": "no share count found", "anchor_found": bool(positions)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="pipeline/tmp_capital/capital-declarations.json")
    parser.add_argument("--state", default="pipeline/state/share_capital.json")
    parser.add_argument("--filings", default="", help="filings.json for sanity checks (default: alongside state)")
    parser.add_argument("--max-age-days", type=int, default=730, help="Ignore declarations older than this")
    args = parser.parse_args()

    import datetime as dt

    input_path = Path(args.input).resolve()
    base_dir = input_path.parent
    data = json.loads(input_path.read_text(encoding="utf-8"))
    state_path = Path(args.state).resolve()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    filings_path = Path(args.filings) if args.filings else state_path.parent / "filings.json"

    # Sanity anchor: the largest disclosed resulting holding per target from our
    # own AMF dealing data. No parsed share count may be smaller than a position
    # someone has disclosed in that company.
    max_disclosed = {}
    if filings_path.exists():
        filings = json.loads(filings_path.read_text(encoding="utf-8"))
        first_num = re.compile(r"\d[\d .,\u00a0\u202f]*")
        for row in filings.get("transactions", []):
            target_key = normalise_target_key(row.get("target"))
            if not target_key:
                continue
            m = first_num.search(str(row.get("resulting_holding") or ""))
            if not m:
                continue
            digits = re.sub(r"[^0-9]", "", m.group())
            if not digits:
                continue
            value = int(digits)
            if value > max_disclosed.get(target_key, 0):
                max_disclosed[target_key] = value

    cutoff_date = (dt.date.today() - dt.timedelta(days=args.max_age_days)).isoformat()
    state_keys = {normalise_target_key(k): k for k in state if not str(k).startswith("_")}
    summary = []

    for company in data.get("companies", []):
        offeree = str(company.get("offeree") or "").strip()
        declarations = company.get("declarations") or []
        if not offeree:
            continue
        target_key = normalise_target_key(offeree)
        existing_key = state_keys.get(target_key)
        existing = state.get(existing_key) if existing_key else None
        if existing is not None and not isinstance(existing, dict):
            existing = {"total": existing}
        baseline = None
        if existing:
            try:
                baseline = int(str(existing.get("total")).replace(",", "").replace(" ", ""))
            except (TypeError, ValueError):
                baseline = None
        floor = max_disclosed.get(target_key, 0)

        history, rejected, failures = [], [], 0
        for declaration in declarations:
            emitted = str(declaration.get("emission_date") or "")
            if emitted and emitted < cutoff_date:
                continue  # too old to be useful for live-deal percentages
            local = declaration.get("local_pdf")
            if not local:
                failures += 1
                continue
            parsed = parse_pdf(base_dir / local)
            if parsed.get("error"):
                failures += 1
                continue
            shares = parsed["shares"]
            reasons = []
            if floor and shares < floor * 0.95:
                reasons.append(f"below max disclosed holding {floor}")
            if baseline and not (baseline / 2.5 <= shares <= baseline * 2.5):
                reasons.append(f"implausible vs existing total {baseline}")
            if reasons:
                rejected.append({"date": emitted, "total": shares, "why": "; ".join(reasons)})
                continue
            history.append({
                "date": emitted,
                "as_at": parsed.get("as_at"),
                "total": shares,
                "voting_rights": parsed.get("votes"),
                "source_url": declaration.get("source_url"),
            })

        if not history:
            if declarations:
                summary.append({"offeree": offeree, "declarations": len(declarations),
                                "kept": 0, "rejected": len(rejected), "failures": failures})
            continue

        history.sort(key=lambda h: h["date"])
        if existing_key is None:
            # No seeded baseline for this company: never auto-create an entry
            # (parsed values cannot be sanity-checked). Log it for manual seeding.
            latest = history[-1]
            summary.append({
                "offeree": offeree, "declarations": len(declarations),
                "kept": len(history), "needs_manual_baseline": True,
                "latest_parsed_total": latest["total"],
                "latest_parsed_date": latest.get("as_at") or latest["date"],
            })
            continue
        key = existing_key
        entry = state[key] if isinstance(state[key], dict) else {"total": state[key]}

        merged = {(h["date"], h["total"]): h for h in (entry.get("history") or [])}
        for h in history:
            merged[(h["date"], h["total"])] = h
        entry["history"] = sorted(merged.values(), key=lambda h: h["date"])

        latest = entry["history"][-1]
        latest_date = latest.get("as_at") or latest["date"]
        overwritten = False
        if not entry.get("manual") and str(latest_date) > str(entry.get("date") or ""):
            entry["total"] = latest["total"]
            entry["date"] = latest_date
            entry["source"] = "AMF 223-16 declaration (info-financiere.gouv.fr)"
            overwritten = True
        state[key] = entry
        summary.append({
            "offeree": offeree, "declarations": len(declarations),
            "kept": len(history), "rejected": len(rejected), "failures": failures,
            "latest_total": latest["total"], "latest_date": latest_date,
            "total_updated": overwritten, "pinned_manual": bool(entry.get("manual")),
            "rejects": rejected[:3],
        })

    state["_note_capital_history"] = (
        "History arrays are maintained automatically from AMF 223-16 declarations "
        "(last 24 months only). Parsed totals are validated against disclosed positions "
        "and the existing figure; the entry's total/date is only replaced by a NEWER "
        "declaration, and never when the entry has \"manual\": true."
    )
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"updated": summary}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
