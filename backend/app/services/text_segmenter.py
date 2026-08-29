import re
from typing import List, Dict, Any

def segment_text_into_events(raw_text: str) -> List[Dict[str, Any]]:
    """
    Splits raw report text into distinct event candidate segments.
    Preserves line number and sentence position for auditability.
    """
    if not raw_text or not raw_text.strip():
        return []

    lines = raw_text.splitlines()
    segments = []
    global_segment_idx = 1

    for line_idx, line in enumerate(lines, start=1):
        line_clean = line.strip()
        if not line_clean:
            continue

        # Split line by semicolons, bullet points, or period sentence boundaries
        raw_clauses = re.split(r';|\. |\n', line_clean)

        for clause_idx, clause in enumerate(raw_clauses, start=1):
            clause_clean = clause.strip(" ;\t-*\t")
            if not clause_clean:
                continue

            # Check if clause contains multiple distinct work items connected by ' and '
            # e.g., "F12 reinforcement completed and 24P201 spool erection started"
            and_parts = re.split(r'\s+and\s+', clause_clean, flags=re.IGNORECASE)
            if len(and_parts) > 1 and all(any(k in p.lower() for k in ["started", "completed", "commenced", "finished", "ongoing", "rebar", "erection", "concreting", "installation", "hydrotesting", "testing", "alignment", "shuttering", "pulling", "laying", "fabrication", "welding"]) for p in and_parts):
                sub_clauses = and_parts
            else:
                sub_clauses = [clause_clean]

            for sub_clause in sub_clauses:
                sub_clean = sub_clause.strip(" ;\t-*\t")
                if not sub_clean:
                    continue
                segments.append({
                    "segment_index": global_segment_idx,
                    "text": sub_clean,
                    "source_position": {
                        "type": "TXT_LINE",
                        "line": line_idx,
                        "clause_index": clause_idx
                    }
                })
                global_segment_idx += 1

    return segments
