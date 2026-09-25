import argparse
import json
import re
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_ADMIN_HTML = Path(__file__).resolve().parents[1] / "admin-index.html"
DEFAULT_CLIENT_HTML = Path(__file__).resolve().parents[1] / "index.html"

# Live deal details for French offer-period companies come from the European
# public offers tracker (europe.arbinsight.co.uk), which publishes its data as
# JSON in the european-public-offers-tracker repository.
DEFAULT_TRACKER_URL = (
    "https://raw.githubusercontent.com/philipshaw-afk/"
    "european-public-offers-tracker/main/data/deals.json"
)

# Tracker target name (normalised) -> AMF offer-period name, for renamed
# companies that cannot be matched by name.
TRACKER_ALIASES = {
    "ESSO": "NORTH ATLANTIC ENERGIES",
}

# Manual fallback values only. Live share-capital numbers now come from the
# admin DATA's share_capital_entries (pipeline/state/share_capital.json in the
# french-opa-admin repository).
CURRENT_SHARE_CAPITAL_OVERRIDES = []

# Populated in main() from the admin DATA blob.
ADMIN_CAPITAL_BY_NORM = {}
ADMIN_CAPITAL_ENTRIES = []


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_int(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    digits = re.sub(r"[^0-9]", "", str(value))
    return int(digits) if digits else None


def normalise_name(value):
    text = clean_text(value).upper()
    text = text.replace("&", " AND ")
    text = re.sub(
        r"\b(SOCIETE ANONYME FRANCAISE|SOCIETE ANONYME|SOCIETE|ANONYME|FRANCAISE|"
        r"SA|SAS|SCA|SE|PLC|LTD|NV|SPA|AG|AB)\b",
        " ",
        text,
    )
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def date_only(value):
    text = clean_text(value)
    if not text:
        return ""
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", text)
    if match:
        return match.group(1)
    return text


def parse_admin_data(path):
    text = path.read_text(encoding="utf-8")
    match = re.search(r"const DATA = (.*?);\n", text, flags=re.S)
    if not match:
        raise ValueError(f"Could not find admin DATA block in {path}")
    return json.loads(match.group(1))


def apply_company_links(admin):
    """Show linked filer names (admin Manage Companies / state/company_links.json)
    under one shared name, so the same firm appears once in each register."""
    links = {
        clean_text(entry.get("sourceName")).upper(): entry
        for entry in admin.get("company_links", [])
        if entry.get("sourceName") and entry.get("sharedName")
    }
    changed = 0
    for row in admin.get("transactions", []):
        original = clean_text(row.get("filer"))
        link = links.get(original.upper())
        if not link:
            continue
        shared = clean_text(link.get("sharedName"))
        if link.get("rule") == "approved (separate entities)":
            row["_entity"] = original  # keeps its own position; added to the group total
        if shared and shared != row.get("filer"):
            row["filer"] = shared
            changed += 1
    return changed


def parse_existing_live(path):
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"/\*LIVE_DATA_START\*/\s*const LIVE = (.*?);\s*/\*LIVE_DATA_END\*/",
        text,
        flags=re.S,
    )
    if not match:
        return {}
    return json.loads(match.group(1))


def deal_type(value):
    text = clean_text(value).lower()
    if "mbo" in text or "mbi" in text:
        return "MBO/MBI"
    if "mandatory" in text:
        return "Mandatory"
    if "minor" in text:
        return "Minority Bid"
    if "merger" in text:
        return "Merger"
    return "Public Offer"


def first_filer_for_notice(transactions):
    result = {}
    for row in transactions:
        amf = row.get("amf_number")
        filer = clean_text(row.get("filer"))
        if amf and filer and amf not in result:
            result[amf] = filer
    return result


def canonical_target_map(admin):
    counts = Counter()
    for notice in admin.get("notice_summaries", []):
        if notice.get("target"):
            counts[clean_text(notice["target"])] += 1
    for row in admin.get("transactions", []):
        if row.get("target"):
            counts[clean_text(row["target"])] += 1
    by_norm = {}
    for target, _count in counts.most_common():
        key = normalise_name(target)
        if key and key not in by_norm:
            by_norm[key] = target
    return by_norm


def canonical_target(name, target_map):
    return target_map.get(normalise_name(name), clean_text(name))


def build_deal_maps(admin, target_map):
    deals = admin.get("french_public_offer_deals_last_five_years", {}).get("deals", [])
    by_norm = {}
    for deal in deals:
        target = canonical_target(deal.get("target"), target_map)
        item = {
            "deal_number": deal.get("deal_number", ""),
            "target": target,
            "country": "France",
            "country_code": "FR",
            "bidder": clean_text(deal.get("ultimate_bidder")) or clean_text(deal.get("offeror_named")),
            "deal_type": deal_type(deal.get("type_of_deal")),
            "status": clean_text(deal.get("status_of_deal")),
            "attitude": clean_text(deal.get("deal_attitude")) or "Friendly",
            "consideration": clean_text(deal.get("consideration_type")),
            "equity_value_eur_m": deal.get("implied_total_equity_value"),
            "announced": deal.get("date_announced") or "",
            "completed": deal.get("date_completed") or "",
            "share_capital": parse_int(deal.get("target_ordinary_shares")),
        }
        by_norm[normalise_name(target)] = item
        by_norm.setdefault(normalise_name(deal.get("target")), item)
    return by_norm


def share_capital_override_for(target):
    key = normalise_name(target)
    for row in CURRENT_SHARE_CAPITAL_OVERRIDES:
        if normalise_name(row.get("target")) == key:
            return row
    return None


def share_capital_for_target(target, deal_by_norm):
    override = share_capital_override_for(target)
    if override:
        return parse_int(override.get("total"))
    admin_row = ADMIN_CAPITAL_BY_NORM.get(normalise_name(target))
    if admin_row:
        return parse_int(admin_row.get("total"))
    return parse_int(deal_by_norm.get(normalise_name(target), {}).get("share_capital"))


def build_share_capital_entries(deal_by_norm):
    entries = []
    seen = set()
    for deal in deal_by_norm.values():
        target = clean_text(deal.get("target"))
        total = parse_int(deal.get("share_capital"))
        if not target or not total:
            continue
        date = deal.get("completed") or deal.get("announced") or ""
        key = (normalise_name(target), date, total)
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            {
                "target": target,
                "date": date,
                "total": total,
                "type": "Ordinary shares",
                "source": "French deals 5 years.xlsx",
            }
        )

    for row in list(ADMIN_CAPITAL_ENTRIES) + list(CURRENT_SHARE_CAPITAL_OVERRIDES):
        target = clean_text(row.get("target"))
        total = parse_int(row.get("total"))
        date = row.get("date") or ""
        if not target or not total:
            continue
        key = (normalise_name(target), date, total)
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            {
                "target": target,
                "date": date,
                "total": total,
                "type": clean_text(row.get("type")) or "Ordinary shares",
                "source": clean_text(row.get("source")) or "Admin share_capital.json",
            }
        )

    return sorted(entries, key=lambda row: (normalise_name(row["target"]), row.get("date", "")))


MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def iso_date(value):
    """Tracker dates come as '25-Sep-2026', '8 Oct 2026' or '31 October 2026'."""
    text = clean_text(value)
    if not text:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return text[:10]
    match = re.match(r"^(\d{1,2})[\s-]+([A-Za-z]{3,})[\s-]+(\d{4})$", text)
    if match and match.group(2)[:3].lower() in MONTHS:
        return f"{int(match.group(3)):04d}-{MONTHS[match.group(2)[:3].lower()]:02d}-{int(match.group(1)):02d}"
    return text


def load_tracker_deals(source):
    """Return the tracker's French deals, or [] if the tracker is unreachable."""
    if not source:
        return []
    try:
        if re.match(r"^https?://", source):
            with urllib.request.urlopen(source, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        else:
            payload = json.loads(Path(source).read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001 - enrichment must never break the build
        print(f"WARNING: tracker deals unavailable ({error}); French rows use AMF data only.")
        return []
    deals = payload.get("deals", payload) if isinstance(payload, dict) else payload
    return [deal for deal in deals if deal.get("c") == "FR" or deal.get("co") == "France"]


def match_tracker_deal(offeree, tracker_deals):
    """Match an AMF offer-period company to a tracker deal by name."""
    wanted = normalise_name(offeree)
    if not wanted:
        return None
    candidates = []
    for deal in tracker_deals:
        key = normalise_name(deal.get("t"))
        key = normalise_name(TRACKER_ALIASES.get(key, key))
        if key == wanted:
            return deal
        if key.startswith(wanted + " ") or wanted.startswith(key + " "):
            candidates.append(deal)
    return candidates[0] if len(candidates) == 1 else None


def deal_is_current(deal, offer_start):
    """A database deal only describes the live offer if it has not already
    completed / failed before the current offer period began (e.g. Eurobio's
    2024 take-private versus its September 2026 offer)."""
    if not deal:
        return False
    status = clean_text(deal.get("status")).lower()
    if status in ("", "pending", "proposed"):
        return True
    completed = date_only(deal.get("completed"))
    return bool(completed and offer_start and completed >= offer_start)


def build_current_targets(admin, deal_by_norm, target_map, tracker_deals=()):
    companies = admin.get("offer_period_companies_from_amf_xlsx", {}).get("companies", [])
    targets = []
    for company in companies:
        target = canonical_target(company.get("offeree"), target_map)
        offer_start = date_only(company.get("offer_announced"))
        deal = deal_by_norm.get(normalise_name(target), {})
        if not deal_is_current(deal, offer_start):
            deal = {}
        tracked = match_tracker_deal(company.get("offeree"), tracker_deals) or {}
        offeror = clean_text(company.get("offeror"))
        targets.append(
            {
                "country": "France",
                "country_code": "FR",
                "target": target,
                "bidder": clean_text(tracked.get("b")) or offeror,
                "offeror": offeror,
                "deal_type": clean_text(tracked.get("tp")) or deal.get("deal_type") or "Public Offer",
                "attitude": clean_text(tracked.get("at")) or deal.get("attitude") or "Friendly",
                "announced": offer_start or deal.get("announced") or "",
                "offer_period_start": offer_start,
                "expected_completion": iso_date(tracked.get("ec")),
                "equity_value_eur_m": tracked.get("v") if tracked.get("v") is not None else deal.get("equity_value_eur_m"),
                "premium_pct": tracked.get("p"),
                "consideration": deal.get("consideration") or "",
                "isin": clean_text(company.get("isin")),
                "deal_source": "European public tracker" if tracked else ("M&A Monitor DataBase" if deal else "AMF offer-period list"),
            }
        )
    return targets


def build_europe_current_targets(admin):
    europe = admin.get("europe_regulatory", {})
    rows = []
    seen = set()
    for row in europe.get("current_targets", []):
        if row.get("country_code") == "FR" or clean_text(row.get("country")) == "France":
            continue
        target = clean_text(row.get("target"))
        country = clean_text(row.get("country"))
        key = (normalise_name(target), clean_text(row.get("country_code")) or country)
        if not target or not country or key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "country": country,
                "country_code": clean_text(row.get("country_code")),
                "target": target,
                "bidder": clean_text(row.get("bidder")),
                "deal_type": clean_text(row.get("deal_type")) or "Public Offer",
                "attitude": clean_text(row.get("attitude")) or "Friendly",
                "announced": clean_text(row.get("announced")),
                "expected_completion": clean_text(row.get("expected_completion")),
                "equity_value_eur_m": row.get("equity_value_eur_m"),
                "sector": clean_text(row.get("sector")),
                "consideration": clean_text(row.get("consideration")),
            }
        )
    return rows


def build_historic_targets(admin, existing_live, deal_by_norm, current_targets, target_map):
    current_norms = {normalise_name(row["target"]) for row in current_targets}
    notice_counts = Counter(clean_text(row.get("target")) for row in admin.get("notice_summaries", []))
    historic = []
    for key, deal in deal_by_norm.items():
        if not key or key in current_norms:
            continue
        item = dict(deal)
        item["filings_collected"] = notice_counts.get(item["target"], 0)
        historic.append(item)

    # Keep the earlier Zodiac test case in the public mockup even though it sits outside
    # the five-year workbook.
    seen = {normalise_name(row["target"]) for row in historic}
    for row in existing_live.get("historic_targets", []):
        key = normalise_name(row.get("target"))
        if key and key not in seen:
            item = dict(row)
            item["target"] = canonical_target(item.get("target"), target_map)
            item["filings_collected"] = notice_counts.get(item["target"], item.get("filings_collected", 0))
            historic.append(item)
            seen.add(key)

    return sorted(historic, key=lambda item: (item.get("completed") or "", item.get("target") or ""), reverse=True)


def build_filings(admin, current_targets):
    filer_by_notice = first_filer_for_notice(admin.get("transactions", []))
    current_norms = {normalise_name(row["target"]) for row in current_targets}
    # Filings made before the current offer period began belong to an earlier
    # offer for the same company (e.g. Eurobio 2024) and go to the archive.
    offer_start = {
        normalise_name(row["target"]): row.get("offer_period_start") or ""
        for row in current_targets
        if row.get("country_code") == "FR"
    }
    filings = []
    historic_filings = []
    for notice in admin.get("notice_summaries", []):
        target = clean_text(notice.get("target"))
        if not target:
            continue
        holder = filer_by_notice.get(notice.get("amf_number"), "")
        details = "; ".join(clean_text(value) for value in notice.get("notice_level_resulting_holdings", []) if clean_text(value))
        row = {
            "country": "France",
            "country_code": "FR",
            "target": target,
            "bidder": "",
            "published_date": notice.get("document_date") or date_only(notice.get("date_information")) or date_only(notice.get("published_at")),
            "holder": holder,
            "declarant": holder,
            "holding": "",
            "percentage": None,
            "filing_type": "AMF dealing disclosure during offer (DeclarationAchatVente)",
            "instrument_type": "Purchases & sales",
            "title": f"AMF {notice.get('amf_number', '')}".strip(),
            "details": details,
            "isin": "",
            "source": "AMF BDIF",
            "source_url": notice.get("document_url") or "",
        }
        key = normalise_name(target)
        start = offer_start.get(key, "")
        if key in current_norms and not (start and row["published_date"] and row["published_date"] < start):
            filings.append(row)
        else:
            historic_filings.append(row)
    return filings, historic_filings


def build_europe_filings(admin):
    europe = admin.get("europe_regulatory", {})
    rows = []
    for row in europe.get("filings", []):
        if row.get("country_code") == "FR" or clean_text(row.get("country")) == "France":
            continue
        rows.append(
            {
                "country": clean_text(row.get("country")),
                "country_code": clean_text(row.get("country_code")),
                "target": clean_text(row.get("target")),
                "bidder": clean_text(row.get("bidder")),
                "published_date": clean_text(row.get("published_date") or row.get("date")),
                "holder": clean_text(row.get("holder") or row.get("declarant")),
                "declarant": clean_text(row.get("declarant") or row.get("holder")),
                "holding": clean_text(row.get("holding")),
                "percentage": row.get("percentage"),
                "filing_type": clean_text(row.get("filing_type")),
                "instrument_type": clean_text(row.get("instrument_type")),
                "title": clean_text(row.get("title")),
                "details": clean_text(row.get("details")),
                "isin": clean_text(row.get("isin")),
                "source": clean_text(row.get("source")),
                "source_url": clean_text(row.get("source_url")),
            }
        )
    return rows


def build_transactions(admin):
    notice_dates = {
        notice.get("amf_number"): notice.get("document_date")
        for notice in admin.get("notice_summaries", [])
        if notice.get("amf_number")
    }
    transactions = []
    for row in admin.get("transactions", []):
        target = clean_text(row.get("target"))
        if not target:
            continue
        transactions.append(
            {
                "target": target,
                "filer": clean_text(row.get("filer")),
                "reported": notice_dates.get(row.get("amf_number"))
                or date_only(row.get("published_at"))
                or date_only(row.get("date_information")),
                "dealing": row.get("transaction_date") or "",
                "operation": clean_text(row.get("operation")),
                "op_type": row.get("operation_type") or "",
                "instr": row.get("instrument_type") or "",
                "qty": row.get("quantity") or 0,
                "price": row.get("price_eur") or "",
                "resulting": row.get("resulting_holding") or "",
                "amf": row.get("amf_number") or "",
                "url": row.get("document_url") or "",
            }
        )
    return transactions


def parse_holding(value):
    text = clean_text(value).replace("\u00a0", " ")
    if not text:
        return {"kind": None, "value": None, "holding_type": None}
    match = re.search(r"(-)?\s*([0-9][0-9 .,\u00a0]*)", text)
    if not match:
        return {"kind": None, "value": None, "holding_type": None}
    number = int(re.sub(r"[^0-9]", "", match.group(2)))
    lowered = text.lower()
    if match.group(1) or "short" in lowered:
        return {"kind": "short", "value": number, "holding_type": "short"}
    derivative_words = (
        "equity swap",
        "swap",
        "cfd",
        "option",
        "derivative",
        "instrument",
        "oceane",
        "obligation",
    )
    if any(word in lowered for word in derivative_words):
        return {"kind": "long", "value": number, "holding_type": "derivative"}
    if "action" in lowered or "droit" in lowered or "share" in lowered or "voting" in lowered:
        return {"kind": "long", "value": number, "holding_type": "share"}
    return {"kind": "long", "value": number, "holding_type": "unknown"}


def sum_known(values):
    known = [value for value in values if value is not None]
    return sum(known) if known else None


def latest_positions(rows):
    """Latest (share long, derivative long, short) from rows sorted oldest first."""
    share_long = derivative_long = short_shares = None
    for row in reversed(rows):
        holding = parse_holding(row.get("resulting_holding"))
        if holding["value"] is None:
            continue
        if holding["kind"] == "short" and short_shares is None:
            short_shares = holding["value"]
        elif holding["kind"] == "long":
            is_derivative = (
                row.get("instrument_type") == "Derivative"
                or holding["holding_type"] == "derivative"
            )
            if is_derivative and derivative_long is None:
                derivative_long = holding["value"]
            elif not is_derivative and share_long is None:
                share_long = holding["value"]
        if share_long is not None and derivative_long is not None and short_shares is not None:
            break
    return share_long, derivative_long, short_shares


def first_positions(rows):
    """Earliest (share long, derivative long) from rows sorted oldest first, so
    the register can show a "First seen %" and a % change over time."""
    first_share_long = first_derivative_long = None
    for row in rows:
        holding = parse_holding(row.get("resulting_holding"))
        if holding["value"] is None:
            continue
        if holding["kind"] == "long":
            is_derivative = (
                row.get("instrument_type") == "Derivative"
                or holding["holding_type"] == "derivative"
            )
            if is_derivative and first_derivative_long is None:
                first_derivative_long = holding["value"]
            elif not is_derivative and first_share_long is None:
                first_share_long = holding["value"]
        if first_share_long is not None and first_derivative_long is not None:
            break
    return first_share_long, first_derivative_long


def build_registers(admin, deal_by_norm):
    by_target_filer = defaultdict(list)
    for row in admin.get("transactions", []):
        target = clean_text(row.get("target"))
        filer = clean_text(row.get("filer"))
        if target and filer:
            by_target_filer[(target, filer)].append(row)

    registers = defaultdict(list)
    for (target, filer), rows in by_target_filer.items():
        rows.sort(
            key=lambda row: (
                date_only(row.get("published_at")) or date_only(row.get("date_information")) or "",
                row.get("transaction_date") or "",
                row.get("amf_number") or "",
            )
        )
        # Each legal entity keeps its own latest position; entities brought
        # together by an approved "separate entities" link are added up.
        by_entity = defaultdict(list)
        for row in rows:
            by_entity[row.get("_entity") or filer].append(row)
        latest = [latest_positions(entity_rows) for entity_rows in by_entity.values()]
        share_long = sum_known(item[0] for item in latest)
        derivative_long = sum_known(item[1] for item in latest)
        short_shares = sum_known(item[2] for item in latest)
        long_total = None
        if share_long is not None or derivative_long is not None:
            long_total = (share_long or 0) + (derivative_long or 0)
        last = rows[-1]
        share_capital = share_capital_for_target(target, deal_by_norm)
        pct = None
        if share_capital and long_total is not None:
            pct = long_total / share_capital * 100

        # First-seen holding: same per-metric "earliest disclosed" scan as the
        # "last" block above, but walking forward from the oldest row so the
        # register can show a "First seen %" and a % change over time.
        earliest = [first_positions(entity_rows) for entity_rows in by_entity.values()]
        first_share_long = sum_known(item[0] for item in earliest)
        first_derivative_long = sum_known(item[1] for item in earliest)
        first_long_total = None
        if first_share_long is not None or first_derivative_long is not None:
            first_long_total = (first_share_long or 0) + (first_derivative_long or 0)
        first = rows[0]
        first_date = (
            date_only(first.get("published_at"))
            or date_only(first.get("date_information"))
            or first.get("transaction_date")
            or ""
        )
        first_pct = None
        if share_capital and first_long_total is not None:
            first_pct = first_long_total / share_capital * 100

        registers[target].append(
            {
                "investor": filer,
                "last_date": date_only(last.get("published_at"))
                or date_only(last.get("date_information"))
                or last.get("transaction_date")
                or "",
                "filings": len({row.get("amf_number") for row in rows if row.get("amf_number")}),
                "long_shares": long_total,
                "share_long": share_long or 0,
                "derivative_long": derivative_long or 0,
                "short_shares": short_shares or 0,
                "pct": pct,
                "first_date": first_date,
                "first_shares": first_long_total,
                "first_pct": first_pct,
                "source": "AMF BDIF",
                "source_url": last.get("document_url") or "",
            }
        )

    return {
        target: sorted(
            rows,
            key=lambda row: (
                row.get("pct") if row.get("pct") is not None else -1,
                row.get("long_shares") or 0,
            ),
            reverse=True,
        )
        for target, rows in registers.items()
    }


def replace_live_block(path, live):
    text = path.read_text(encoding="utf-8")
    block = (
        "/*LIVE_DATA_START*/\n"
        f"const LIVE = {json.dumps(live, ensure_ascii=False, separators=(',', ':'))};\n"
        "/*LIVE_DATA_END*/"
    )
    updated, count = re.subn(
        r"/\*LIVE_DATA_START\*/.*?/\*LIVE_DATA_END\*/",
        block,
        text,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise ValueError(f"Could not replace LIVE block in {path}")
    path.write_text(updated, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Embed live data from the admin tracker into the client site."
    )
    parser.add_argument("--admin", default=str(DEFAULT_ADMIN_HTML), help="Admin index.html path")
    parser.add_argument("--client", default=str(DEFAULT_CLIENT_HTML), help="Client index.html path")
    parser.add_argument(
        "--tracker",
        default=DEFAULT_TRACKER_URL,
        help="European tracker deals.json (URL or path); pass '' to skip enrichment",
    )
    args = parser.parse_args()
    admin_html = Path(args.admin)
    client_html = Path(args.client)

    admin = parse_admin_data(admin_html)
    linked_rows = apply_company_links(admin)

    global ADMIN_CAPITAL_BY_NORM, ADMIN_CAPITAL_ENTRIES
    ADMIN_CAPITAL_ENTRIES = [
        entry
        for entry in (admin.get("share_capital_entries") or [])
        if parse_int(entry.get("total"))
    ]
    ADMIN_CAPITAL_BY_NORM = {}
    for entry in sorted(ADMIN_CAPITAL_ENTRIES, key=lambda e: str(e.get("date") or "")):
        key = normalise_name(entry.get("target"))
        if key:
            ADMIN_CAPITAL_BY_NORM[key] = entry

    existing_live = parse_existing_live(client_html)
    target_map = canonical_target_map(admin)
    deal_by_norm = build_deal_maps(admin, target_map)
    tracker_deals = load_tracker_deals(args.tracker)
    current_targets = build_current_targets(admin, deal_by_norm, target_map, tracker_deals)
    current_targets.extend(build_europe_current_targets(admin))
    historic_targets = build_historic_targets(admin, existing_live, deal_by_norm, current_targets, target_map)
    filings, historic_filings = build_filings(admin, current_targets)
    filings.extend(build_europe_filings(admin))
    transactions = build_transactions(admin)
    registers = build_registers(admin, deal_by_norm)
    share_capital_entries = build_share_capital_entries(deal_by_norm)

    live = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "current_targets": current_targets,
        "filings": filings,
        "registers": registers,
        "transactions": transactions,
        "share_capital_entries": share_capital_entries,
        "historic_targets": historic_targets,
        "historic_filings": historic_filings,
        "europe_sources": admin.get("europe_regulatory", {}).get("regulatory_sources", []),
    }
    replace_live_block(client_html, live)

    print(
        json.dumps(
            {
                "client_html": str(client_html),
                "current_targets": len(current_targets),
                "transaction_rows_renamed_by_company_links": linked_rows,
                "french_targets_enriched_from_tracker": sum(
                    1 for row in current_targets if row.get("deal_source") == "European public tracker"
                ),
                "filings": len(filings),
                "registers": len(registers),
                "transactions": len(transactions),
                "share_capital_entries": len(share_capital_entries),
                "historic_targets": len(historic_targets),
                "historic_filings": len(historic_filings),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
