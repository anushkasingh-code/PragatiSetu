import os
import sys
import pandas as pd

# Ensure project root is accessible
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.services.text_segmenter import segment_text_into_events
from backend.app.services.field_extractors import (
    extract_status,
    extract_percent_complete,
    extract_identifier,
    extract_action,
    extract_location
)

def evaluate_ground_truth():
    dataset_path = os.path.join(PROJECT_ROOT, "dataset", "02_field_report_events.xlsx")
    if not os.path.exists(dataset_path):
        print(f"[ERROR] Ground truth file not found at: {dataset_path}")
        sys.exit(1)

    xl = pd.ExcelFile(dataset_path)
    sheet_name = "Labelled_Events" if "Labelled_Events" in xl.sheet_names else ("Events" if "Events" in xl.sheet_names else xl.sheet_names[0])
    df_ground_truth = pd.read_excel(dataset_path, sheet_name=sheet_name)
    total_records = len(df_ground_truth)
    print(f"Evaluating Event Extraction on {total_records} ground-truth records from 02_field_report_events.xlsx (sheet: '{sheet_name}')...\n")

    status_matches = 0
    pct_matches = 0
    id_matches = 0
    loc_matches = 0

    for _, row in df_ground_truth.iterrows():
        row_dict = row.to_dict()
        raw_text = str(row_dict["raw_text"])
        true_status = str(row_dict.get("ground_truth_status") or row_dict.get("status") or "").strip() or None
        true_pct_val = row_dict.get("reported_percent_complete") if pd.notnull(row_dict.get("reported_percent_complete")) else row_dict.get("progress_percentage")
        true_pct = float(str(true_pct_val)) if pd.notnull(true_pct_val) and str(true_pct_val).strip() != "" else None
        true_id = str(row_dict.get("ground_truth_identifier") or row_dict.get("equipment_or_line_id") or "").strip() or None
        true_loc = str(row_dict.get("ground_truth_location") or row_dict.get("location") or "").strip() or None

        pred_status = extract_status(raw_text)
        pred_pct = extract_percent_complete(raw_text)
        pred_id = extract_identifier(raw_text)
        pred_loc = extract_location(raw_text)

        if pred_status == true_status:
            status_matches += 1
        if (pred_pct is not None and true_pct is not None and abs(pred_pct - true_pct) < 0.1) or (pred_pct is None and true_pct is None):
            pct_matches += 1
        if pred_id and true_id and (pred_id.lower() in true_id.lower() or true_id.lower() in pred_id.lower()):
            id_matches += 1
        if pred_loc and true_loc and (pred_loc.lower() in true_loc.lower() or true_loc.lower() in pred_loc.lower()):
            loc_matches += 1

    print("--- Event Extraction Evaluation Results ---")
    print(f"Total Ground Truth Records: {total_records}")
    print(f"Status Match Accuracy: {status_matches / total_records * 100:.2f}% ({status_matches}/{total_records})")
    print(f"Percent Complete Match Accuracy: {pct_matches / total_records * 100:.2f}% ({pct_matches}/{total_records})")
    print(f"Identifier Extraction Match: {id_matches / total_records * 100:.2f}% ({id_matches}/{total_records})")
    print(f"Location Extraction Match: {loc_matches / total_records * 100:.2f}% ({loc_matches}/{total_records})")
    print("\n[NOTE] Matching to baseline activity IDs is explicitly deferred to later milestones.")

if __name__ == "__main__":
    evaluate_ground_truth()
