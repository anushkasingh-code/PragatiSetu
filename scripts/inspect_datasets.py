import os
import pandas as pd

DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset")
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

OUTPUT_MD = os.path.join(DOCS_DIR, "DATASET_SCHEMA.md")

xlsx_files = [
    "01_baseline_schedule.xlsx",
    "02_field_report_events.xlsx",
    "03_daily_progress_reports.xlsx",
    "04_discipline_progress_reports.xlsx",
    "05_activity_terminology_dictionary.xlsx",
    "06_identifier_normalization_dictionary.xlsx",
    "07_dataset_test_split.xlsx",
    "08_project_beta_baseline.xlsx",
    "09_project_beta_reports.xlsx"
]

md_files = [
    "10_dataset_quality_report.md"
]

lines = []
lines.append("# PragatiSetu — Ground Truth Dataset Schema Documentation\n")
lines.append("> **IMPORTANT NOTICE**: This dataset is entirely **SYNTHETIC** development/evaluation ground truth. It is NOT real Oil India Limited data.\n")
lines.append("## Dataset Overview\n")
lines.append("- **PragatiSetu**: 75 baseline schedule activities, 400 labelled field events (280 dev, 60 val, 60 test).")
lines.append("- **Project Beta**: 30 baseline schedule activities, 100 field report events.")
lines.append("- **QA Checks**: 45 checks reported as PASS in `10_dataset_quality_report.md`.\n")
lines.append("---\n")
lines.append("## Detailed File Inspection\n")

for fname in xlsx_files:
    fpath = os.path.join(DATASET_DIR, fname)
    if not os.path.exists(fpath):
        lines.append(f"### File: `{fname}` — NOT FOUND\n")
        continue

    excel_obj = pd.ExcelFile(fpath)
    sheet_names = excel_obj.sheet_names
    lines.append(f"### File: `{fname}`")
    lines.append(f"- **Workbook Sheets**: `{sheet_names}`\n")

    for sheet in sheet_names:
        df = pd.read_excel(fpath, sheet_name=sheet)
        row_count, col_count = df.shape
        lines.append(f"#### Sheet: `{sheet}`")
        lines.append(f"- **Total Rows**: `{row_count}`")
        lines.append(f"- **Total Columns**: `{col_count}`")
        lines.append(f"- **Columns**: `{list(df.columns)}`\n")

        lines.append("| Column Name | Data Type | Null Count | Sample Value |")
        lines.append("| --- | --- | --- | --- |")
        for col in df.columns:
            dtype_str = str(df[col].dtype)
            null_cnt = int(df[col].isnull().sum())
            sample_val = str(df[col].dropna().iloc[0]) if not df[col].dropna().empty else "None"
            lines.append(f"| `{col}` | `{dtype_str}` | `{null_cnt}` | `{sample_val}` |")
        lines.append("\n")

for mname in md_files:
    mpath = os.path.join(DATASET_DIR, mname)
    lines.append(f"### File: `{mname}`")
    if os.path.exists(mpath):
        with open(mpath, "r", encoding="utf-8") as f:
            content = f.read()
        lines.append(f"**Content Snippet**:\n```markdown\n{content[:500]}...\n```\n")

with open(OUTPUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Generated dataset schema documentation at: {OUTPUT_MD}")
