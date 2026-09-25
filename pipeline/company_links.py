#!/usr/bin/env python3
"""Link AMF filer names that are the same firm written differently.

Used by build_app.py on every daily build. Reads and rewrites
pipeline/state/company_links.json:

  approved     groups Phil has approved (always applied, never recomputed);
               "separate_entities": true means each name holds its own position
               (register rows add them up) rather than being one filer's spellings
  rejected     pairs of names that must never be linked or suggested
  auto         groups linked automatically by the safe rules below (recomputed)
  suggestions  same-brand groups that may be different entities (for review)
  fragments    names that look like parser fragments ("Co.", "Management LP")

Safe rules (auto-linked):
  1. Same name apart from case, accents, punctuation, "&" spacing, text in
     brackets, legal form (Ltd, LLP, SAS, Inc, S.a r.l. ...), a trailing "UK"
     and Holding/Holdings.
  2. A shortened name ("Samson Rock", "Caisse des dépôts") that is the start of
     exactly one longer name, unless the only extra words are Holding/Group.
People ("M. ...", "Mme ...") are only linked under rule 1.
"""
import datetime as dt
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent / "state" / "company_links.json"

LEGAL = {
    "LLP", "LTD", "LIMITED", "LP", "LLC", "INC", "INCORPORATED", "PLC", "SA", "SAS",
    "SE", "AG", "GMBH", "SARL", "SCA", "SC", "NV", "BV", "CO", "CORP", "CORPORATION",
    "SRL", "SPA", "AB", "ASA", "AS", "SLP", "KG", "UK",
}
GENERIC = {
    "MANAGEMENT", "HOLDING", "INTERNATIONAL", "CAPITAL", "ASSET", "PARTNERS", "BANK",
    "GROUP", "GROUPE", "SOCIETE", "GENERALE", "EUROPE", "COMMERCIAL", "INVESTMENT",
    "INVESTMENTS", "RENEWABLE", "BIDCO", "FUND", "FONDS", "ET", "DE", "DES", "DU", "AND",
    "CONSIGNATIONS", "ADVISORS", "REGION", "GLOBAL", "GESTION", "FINANCE", "SECURITIES",
}
CONNECTORS = {"ET", "DE", "DES", "DU", "AND", "OF"}
BRAND_STOP = {
    "LA", "LE", "LES", "THE", "FPCI", "FCP", "FCPI", "FONDS", "GROUPE", "SOCIETE", "EPIC",
    "BANQUE", "FINANCIERE", "CREDIT", "CAISSE", "HOLDING",
}
PERSON_RE = re.compile(r"^(?:M|MME|MR|MRS|MS|DR|MLLE)\b\.?\s", re.I)


def fold(name):
    text = unicodedata.normalize("NFD", str(name or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).upper()
    text = re.sub(r"\([^)]*\)", " ", text).replace("&", " AND ")
    tokens = re.sub(r"[^A-Z0-9]+", " ", text).split()
    merged, run = [], []
    for token in tokens + [""]:  # "S A S" -> "SAS", "J P J S" -> "JPJS"
        if len(token) == 1 and token.isalpha():
            run.append(token)
            continue
        if run:
            merged.append("".join(run))
            run = []
        if token:
            merged.append(token)
    return merged


def is_person(name):
    return bool(PERSON_RE.match(str(name or "").strip()))


def entity_key(name):
    tokens = ["HOLDING" if t == "HOLDINGS" else t for t in fold(name)]
    if is_person(name):
        return " ".join(tokens)
    while tokens and (tokens[-1] in LEGAL or tokens[-1] in CONNECTORS):
        if len(tokens) == 1:
            break
        tokens.pop()
    return " ".join(tokens)


def is_fragment(name):
    raw = str(name or "").strip()
    if not raw or re.match(r"^\d", raw) or re.search(r"\d{3}C\d{4}", raw):
        return True
    if raw[:1].islower():  # "et consignations", "et de"
        return True
    if is_person(raw):
        return len(fold(raw)) < 2 + 1  # "M. Romain" - title plus one word
    words = [re.sub(r"\d+$", "", w) for w in entity_key(raw).split()]
    return all(w in GENERIC or w in LEGAL or not w for w in words)


def tidy(name):
    return re.sub(r"\s+", " ", re.sub(r"&(?=\w)", "& ", str(name))).strip()


def pick_shared(names, counts):
    """Fullest form first, then most used, preferring mixed case."""
    longest = max(len(entity_key(n).split()) for n in names)
    full = [n for n in names if len(entity_key(n).split()) == longest]
    best = sorted(full, key=lambda n: (-counts.get(n, 0), n.isupper(), -len(n)))[0]
    return tidy(best)


class Groups:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        self.parent[self.find(a)] = self.find(b)

    def groups(self):
        out = defaultdict(list)
        for x in list(self.parent):
            out[self.find(x)].append(x)
        return [sorted(v) for v in out.values() if len(v) > 1]


def load_state(path=STATE_FILE):
    if Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return {}


def compute(counts, state, targets=None):
    """counts: {filer name: number of transaction rows};
    targets: {filer name: set of target companies} (for fragment matching)."""
    targets = targets or {}
    names = sorted(n for n in counts if n)
    rejected = {frozenset(p) for p in state.get("rejected", []) if len(p) == 2}
    approved = [g for g in state.get("approved", []) if len(g.get("names", [])) > 1]
    approved_names = {n for g in approved for n in g["names"]}

    def allowed(a, b):
        return frozenset((a, b)) not in rejected

    fragments = [n for n in names if is_fragment(n)]
    fragment_set = set(fragments)
    candidates = [n for n in names if n not in fragment_set]

    auto = Groups()
    reasons = {}
    by_key = defaultdict(list)
    for n in candidates:
        by_key[entity_key(n)].append(n)
    for key, members in by_key.items():
        if len(key) < 3 or len(members) < 2:
            continue
        for other in members[1:]:
            if allowed(members[0], other):
                auto.union(members[0], other)
        reasons[key] = "same name apart from case, punctuation or legal form"

    companies = [k for k in by_key if not is_person(by_key[k][0])]
    for short in companies:
        words = short.split()
        if len(words) < 2 and not (words and words[-1] in CONNECTORS):
            continue
        longer = [k for k in companies if k.startswith(short + " ")]
        if len(longer) != 1:
            continue
        extra = set(longer[0][len(short):].split())
        if extra <= {"HOLDING", "GROUP", "GROUPE"}:
            continue
        a, b = by_key[short][0], by_key[longer[0]][0]
        if allowed(a, b):
            auto.union(a, b)

    auto_groups = []
    for members in auto.groups():
        if set(members) & approved_names:
            continue  # Phil's approved grouping takes precedence
        rule = ("shortened name" if len({entity_key(m) for m in members}) > 1
                else "same name apart from case, punctuation or legal form")
        auto_groups.append({"names": members, "shared": pick_shared(members, counts), "rule": rule})

    # Suggestions: same first distinctive word, not already in one group.
    grouped = {}
    for g in auto_groups + approved:
        for n in g["names"]:
            grouped[n] = g.get("shared") or g["names"][0]
    brand = defaultdict(set)
    for n in candidates:
        if is_person(n):
            continue
        words = [w for w in entity_key(n).split() if w not in BRAND_STOP]
        if words:
            brand[words[0]].add(n)
    suggestions = []
    for word, members in sorted(brand.items()):
        units = {grouped.get(n, n) for n in members}
        if len(units) < 2:
            continue
        members = sorted(members)
        pairs_ok = any(allowed(a, b) and grouped.get(a, a) != grouped.get(b, b)
                       for a in members for b in members if a < b)
        if not pairs_ok:
            continue
        suggestions.append({
            "names": members,
            "shared": pick_shared(members, counts),
            "reason": f"same brand ({word.title()}) - may be different entities",
        })

    # Fragments ("Holding LLC", "et consignations") that end or start a single
    # full name filing on the same target: suggest the full name for review.
    for frag in fragments:
        frag_tokens = fold(frag)
        if not frag_tokens or re.match(r"^\d", frag) or len("".join(frag_tokens)) < 2:
            continue
        matches = set()
        for full in candidates:
            if not (targets.get(frag, set()) & targets.get(full, set())):
                continue
            full_tokens = fold(full)
            n = len(frag_tokens)
            if len(full_tokens) > n and (full_tokens[-n:] == frag_tokens or full_tokens[:n] == frag_tokens):
                matches.add(grouped.get(full, full))
        if len(matches) == 1:
            full = matches.pop()
            if allowed(frag, full) and not any(frag in g["names"] for g in approved):
                shared_targets = ", ".join(sorted(targets.get(frag, set()))[:2])
                suggestions.append({
                    "names": [frag, full],
                    "shared": full,
                    "reason": f"incomplete name - same target ({shared_targets})",
                })

    links = []
    for g in approved + auto_groups:
        for n in g["names"]:
            if n != g["shared"]:
                if g in approved:
                    rule = "approved (separate entities)" if g.get("separate_entities") else "approved"
                else:
                    rule = g["rule"]
                links.append({"sourceName": n, "sharedName": g["shared"], "rule": rule})
    return {
        "links": links,
        "auto": auto_groups,
        "suggestions": suggestions,
        "fragments": [{"name": n, "rows": counts.get(n, 0)} for n in fragments],
    }


def refresh_state(counts, targets=None, path=STATE_FILE):
    state = load_state(path)
    result = compute(counts, state, targets)
    new_state = {
        "_note": (
            "Company-name links for the Manage Companies page. 'approved' and 'rejected' are "
            "kept as they are; 'auto', 'suggestions' and 'fragments' are recomputed on every "
            "daily build by pipeline/company_links.py."
        ),
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "approved": state.get("approved", []),
        "rejected": state.get("rejected", []),
        "auto": result["auto"],
        "suggestions": result["suggestions"],
        "fragments": result["fragments"],
    }
    Path(path).write_text(json.dumps(new_state, indent=2, ensure_ascii=False), encoding="utf-8")
    return result
