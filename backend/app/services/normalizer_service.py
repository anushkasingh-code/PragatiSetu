import os
import re
import pandas as pd
from typing import Optional, Dict

DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "dataset")

_IDENTIFIER_MAP: Dict[str, str] = {}
_TERMINOLOGY_MAP: Dict[str, str] = {}
_DICTIONARIES_LOADED = False

def load_normalization_dictionaries():
    global _IDENTIFIER_MAP, _TERMINOLOGY_MAP, _DICTIONARIES_LOADED
    if _DICTIONARIES_LOADED:
        return

    # 1. Identifier normalization dictionary
    id_path = os.path.join(DATASET_DIR, "06_identifier_normalization_dictionary.xlsx")
    if os.path.exists(id_path):
        try:
            excel_id = pd.ExcelFile(id_path)
            sheet_name = "Normalization" if "Normalization" in excel_id.sheet_names else excel_id.sheet_names[0]
            df_id = pd.read_excel(id_path, sheet_name=sheet_name)
            for _, row in df_id.iterrows():
                canon = str(row.get("canonical_identifier", "")).strip()
                raw = str(row.get("observed_variant", row.get("raw_identifier", ""))).strip().upper()
                if raw and canon:
                    _IDENTIFIER_MAP[raw] = canon
        except Exception:
            pass

    # 2. Activity terminology dictionary
    term_path = os.path.join(DATASET_DIR, "05_activity_terminology_dictionary.xlsx")
    if os.path.exists(term_path):
        try:
            excel_term = pd.ExcelFile(term_path)
            sheet_name = "Terminology" if "Terminology" in excel_term.sheet_names else excel_term.sheet_names[0]
            df_term = pd.read_excel(term_path, sheet_name=sheet_name)
            for _, row in df_term.iterrows():
                canon = str(row.get("canonical_term", row.get("standard_term", ""))).strip()
                alias = str(row.get("synonym_or_alias", row.get("field_term", ""))).strip().lower()
                abbrev = str(row.get("abbreviation", "")).strip().lower() if pd.notnull(row.get("abbreviation")) else ""
                
                if alias and alias != "nan" and canon:
                    _TERMINOLOGY_MAP[alias] = canon
                if abbrev and abbrev != "nan" and canon:
                    _TERMINOLOGY_MAP[abbrev] = canon
        except Exception:
            pass

    _DICTIONARIES_LOADED = True

def normalize_identifier(raw_identifier: Optional[str]) -> Optional[str]:
    if not raw_identifier or not str(raw_identifier).strip():
        return None
    load_normalization_dictionaries()
    clean_raw = str(raw_identifier).strip()
    upper_raw = clean_raw.upper()

    # Dictionary lookup first
    if upper_raw in _IDENTIFIER_MAP:
        return _IDENTIFIER_MAP[upper_raw]
    
    # Deterministic fallback normalization: strip spaces and hyphens, uppercase
    normalized = re.sub(r"[\s\-_]+", "", upper_raw)
    return normalized if normalized else clean_raw

def normalize_action(raw_action: Optional[str]) -> Optional[str]:
    if not raw_action or not str(raw_action).strip():
        return None
    load_normalization_dictionaries()
    clean_action = str(raw_action).strip().lower()

    if clean_action in _TERMINOLOGY_MAP:
        return _TERMINOLOGY_MAP[clean_action]
    
    return clean_action.title()

def normalize_object(raw_object: Optional[str]) -> Optional[str]:
    if not raw_object or not str(raw_object).strip():
        return None
    return str(raw_object).strip().title()

def normalize_location(raw_location: Optional[str]) -> Optional[str]:
    if not raw_location or not str(raw_location).strip():
        return None
    load_normalization_dictionaries()
    clean_loc = str(raw_location).strip()
    upper_loc = clean_loc.upper()

    if upper_loc in _IDENTIFIER_MAP:
        return _IDENTIFIER_MAP[upper_loc]

    # Standardize location spacing & hyphens (e.g. Rack-B -> RACKB)
    return re.sub(r"[\s\-_]+", "", upper_loc)
