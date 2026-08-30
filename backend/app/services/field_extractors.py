import re
import datetime
from typing import Dict, Any, Optional, Tuple

STATUS_PATTERNS = [
    (r"\b(completed|complete|finished|done|accomplished|executed|performed|carried out|wound up)\b", "COMPLETED"),
    (r"\b(ongoing|in progress|continued|progressing|continuing|underway|in-progress|carrying on|in hand)\b", "IN_PROGRESS"),
    (r"\b(commenced|started|began|initiated|begun|kicked off|start ho gaya|start hua)\b", "STARTED"),
    (r"\b(not started|pending|yet to start)\b", "NOT_STARTED")
]

# Negation phrases that invalidate a status match
NEGATION_PREFIXES_REGEX = re.compile(
    r"\b(no work|no activities|not|no one|none|zero|nil|nothing)\s+(was\s+|were\s+|has been\s+|have been\s+)?",
    re.IGNORECASE
)

PERCENT_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|percent|per cent)", re.IGNORECASE)

# Action vocabulary informed by dataset inspection and field terminology
ACTION_PATTERNS = [
    r"\b(hydrostatic testing|hydrotesting|testing|hydrotest)\b",
    r"\b(tie-in|hot tie-in connection|tie in)\b",
    r"\b(cable pulling|cable laying|laying|pulling)\b",
    r"\b(pump alignment|alignment)\b",
    r"\b(shuttering|formwork)\b",
    r"\b(excavation|digging|earthwork)\b",
    r"\b(backfilling|backfill)\b",
    r"\b(concreting|pouring|concrete pouring)\b",
    r"\b(reinforcement|rebar)\b",
    r"\b(erection|installation|installing|erecting)\b",
    r"\b(fabrication|welding|weld)\b",
    r"\b(commissioning|pre-commissioning)\b",
    r"\b(painting|coating)\b",
    r"\b(repair|maintenance|fixing)\b",
    r"\b(drainage|dewatering)\b",
    r"\b(grouting|grout)\b",
    r"\b(insulation|cladding)\b",
    r"\b(inspection|checking|testing)\b",
]

# Object vocabulary
OBJECT_PATTERNS = [
    r"\b(spool|piping spool|pipe)\b",
    r"\b(foundation|footing)\b",
    r"\b(cable tray|cable|wire)\b",
    r"\b(pump|compressor|generator)\b",
    r"\b(support|tray support|structural support|cable tray support)\b",
    r"\b(valve|flange)\b",
    r"\b(substation|panel)\b",
    r"\b(tank|vessel)\b",
    r"\b(drainage|drain)\b",
    r"\b(structure|structural|platform)\b",
    r"\b(road|surface|pavement)\b",
]

# Identifier patterns (e.g. 24P201, 24-P-201, EQ-ALPHA-101, LINE-ALPHA-201, F12, E-301, P-101A)
IDENTIFIER_REGEX = re.compile(
    r"\b(?:[A-Z]{2,4}-[A-Z0-9]+-\d+|LINE-[A-Z0-9]+-\d+|\d+[A-Z]\d+|[A-Z]-\d+[A-Z]?|F\d+|[A-Z]\d+)\b",
    re.IGNORECASE
)

# Location patterns (e.g. Rack B, Plot A, Pipe Rack Unit 1, Substation 3, Area A)
LOCATION_REGEX = re.compile(
    r"\b(?:near|at|in|around|area)\s+([A-Z0-9\s]+?(?:Rack\s+[A-Z0-9]+|Plot\s+[A-Z0-9]+|Substation\s+\d+|Unit\s+\d+|Area\s+[A-Z0-9]+|Room\s+\d+|Control Room|Compressor Area|Pipe Rack Unit \d+))\b|\b(Rack\s+[A-Z0-9]+|Plot\s+[A-Z0-9]+|Substation\s+\d+|Unit\s+\d+|Area\s+[A-Z0-9]+|Pipe Rack Unit \d+|Compressor Area|Control Room)\b",
    re.IGNORECASE
)

QUANTITY_REGEX = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(meters|m|supports|joints|cubic meters|m3|units|pcs|pieces)\b",
    re.IGNORECASE
)

EXPLICIT_DATE_REGEX = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)\b",
    re.IGNORECASE
)

def extract_percent_complete(text: str) -> Optional[float]:
    match = PERCENT_REGEX.search(text)
    if match:
        val = float(match.group(1))
        if 0.0 <= val <= 100.0:
            return val
    return None

def extract_status(text: str) -> Optional[str]:
    # Check if explicit percentage completes provides precise status indication
    pct = extract_percent_complete(text)
    if pct is not None:
        if pct >= 100.0:
            return "COMPLETED"
        elif pct > 0.0:
            return "IN_PROGRESS"
        else:
            return "NOT_STARTED"

    for pattern, status in STATUS_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            # Check for a negation prefix immediately before the matched keyword
            start = m.start()
            prefix_window = text[max(0, start - 30):start]
            if NEGATION_PREFIXES_REGEX.search(prefix_window):
                continue  # Negated — don't count as status
            return status
    return None

def extract_identifier(text: str) -> Optional[str]:
    match = IDENTIFIER_REGEX.search(text)
    if match:
        return match.group(0).strip()
    return None

def extract_action(text: str) -> Optional[str]:
    for pattern in ACTION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None

def extract_object(text: str) -> Optional[str]:
    for pattern in OBJECT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None

def extract_location(text: str) -> Optional[str]:
    match = LOCATION_REGEX.search(text)
    if match:
        loc = match.group(1) or match.group(2)
        if loc:
            return loc.strip()
    return None

def extract_quantity_and_unit(text: str) -> Tuple[Optional[float], Optional[str]]:
    match = QUANTITY_REGEX.search(text)
    if match:
        qty = float(match.group(1))
        unit = match.group(2).strip()
        return qty, unit
    return None, None

def extract_explicit_date(text: str) -> Optional[str]:
    match = EXPLICIT_DATE_REGEX.search(text)
    if match:
        return match.group(1).strip()
    return None
