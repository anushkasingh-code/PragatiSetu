import io
import datetime
from pathlib import Path
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from backend.app.config import settings

VALID_EXTENSIONS = {".txt", ".csv", ".xlsx"}
VALID_DISCIPLINES = {"CIVIL", "PIPING", "MECHANICAL", "ELECTRICAL", "INSTRUMENTATION", "GENERAL"}

# Discovered report schemas from synthetic dataset package
REQUIRED_COLUMNS_DPR = {"dpr_id", "project_id", "date"}
REQUIRED_COLUMNS_DISCIPLINE = {"report_id", "project_id", "discipline"}

class ReportValidationError(Exception):
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

def validate_file_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in VALID_EXTENSIONS:
        raise ReportValidationError(
            code="UNSUPPORTED_FILE_TYPE",
            message=f"Unsupported file extension '{ext}'. Allowed extensions are: {sorted(list(VALID_EXTENSIONS))}",
            details={"filename": filename, "extension": ext, "supported_extensions": sorted(list(VALID_EXTENSIONS))}
        )
    return ext

def validate_file_size(content_length: int) -> None:
    if content_length <= 0:
        raise ReportValidationError(
            code="EMPTY_FILE",
            message="Uploaded file is empty (0 bytes).",
            details={"file_size": content_length}
        )
    if content_length > settings.MAX_FILE_SIZE_BYTES:
        raise ReportValidationError(
            code="FILE_TOO_LARGE",
            message=f"File size ({content_length} bytes) exceeds maximum limit of {settings.MAX_FILE_SIZE_BYTES} bytes.",
            details={"file_size": content_length, "max_limit": settings.MAX_FILE_SIZE_BYTES}
        )

def validate_discipline(discipline: Optional[str]) -> Optional[str]:
    if not discipline:
        return "General"
    disc_upper = discipline.strip().upper()
    if disc_upper not in VALID_DISCIPLINES:
        raise ReportValidationError(
            code="INVALID_DISCIPLINE",
            message=f"Invalid discipline '{discipline}'. Allowed disciplines: {sorted([d.title() for d in VALID_DISCIPLINES])}",
            details={"discipline": discipline, "allowed_disciplines": sorted([d.title() for d in VALID_DISCIPLINES])}
        )
    return discipline.strip().title()

def validate_report_date(report_date_str: Any) -> datetime.date:
    if isinstance(report_date_str, datetime.date):
        return report_date_str
    if not report_date_str or not str(report_date_str).strip():
        raise ReportValidationError(
            code="INVALID_REPORT_DATE",
            message="Report date is missing or empty.",
            details={"report_date": report_date_str}
        )
    try:
        dt = pd.to_datetime(report_date_str).date()
        return dt
    except Exception:
        raise ReportValidationError(
            code="INVALID_REPORT_DATE",
            message=f"Unable to parse report date '{report_date_str}'. Expected format YYYY-MM-DD.",
            details={"report_date": report_date_str}
        )

def validate_file_content(filename: str, content: bytes) -> Tuple[str, str, Optional[pd.DataFrame]]:
    """
    Validates content based on format (TXT, CSV, XLSX).
    Returns tuple: (source_type, raw_text_content, parsed_dataframe)
    """
    ext = validate_file_extension(filename)
    validate_file_size(len(content))

    if ext == ".txt":
        try:
            raw_text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                raw_text = content.decode("latin-1")
            except Exception as e:
                raise ReportValidationError(
                    code="MALFORMED_FILE",
                    message=f"Failed to decode text file with UTF-8 or Latin-1: {str(e)}",
                    details={"error": str(e)}
                )
        
        if not raw_text.strip():
            raise ReportValidationError(
                code="EMPTY_FILE",
                message="TXT file contains only empty whitespace.",
                details={"filename": filename}
            )
        return "TXT", raw_text, None

    elif ext == ".csv":
        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception as e:
            raise ReportValidationError(
                code="MALFORMED_FILE",
                message=f"Malformed CSV file could not be parsed: {str(e)}",
                details={"error": str(e)}
            )
        
        if df.empty or len(df.columns) == 0:
            raise ReportValidationError(
                code="EMPTY_FILE",
                message="CSV file is empty or contains no data rows.",
                details={"rows": len(df), "columns": len(df.columns)}
            )
        
        _validate_spreadsheet_columns(filename, df)
        raw_text = df.to_csv(index=False)
        return "CSV", raw_text, df

    elif ext == ".xlsx":
        try:
            excel_file = pd.ExcelFile(io.BytesIO(content))
            sheets = excel_file.sheet_names
            if not sheets:
                raise ReportValidationError(
                    code="EMPTY_FILE",
                    message="XLSX workbook contains no sheets.",
                    details={"filename": filename}
                )
            
            # Read first sheet or matching sheet
            df = pd.read_excel(excel_file, sheet_name=sheets[0])
        except Exception as e:
            raise ReportValidationError(
                code="MALFORMED_FILE",
                message=f"Malformed XLSX workbook could not be opened: {str(e)}",
                details={"error": str(e)}
            )

        if df.empty or len(df.columns) == 0:
            raise ReportValidationError(
                code="EMPTY_FILE",
                message="XLSX workbook sheet contains no data rows.",
                details={"rows": len(df), "columns": len(df.columns)}
            )

        _validate_spreadsheet_columns(filename, df)
        raw_text = df.to_json(orient="records", date_format="iso")
        return "XLSX", raw_text, df

    raise ReportValidationError(code="UNSUPPORTED_FILE_TYPE", message=f"Unsupported format: {ext}")

def _validate_spreadsheet_columns(filename: str, df: pd.DataFrame) -> None:
    cols = {str(c).strip().lower() for c in df.columns}
    fname_lower = filename.lower()

    if "dpr" in fname_lower or REQUIRED_COLUMNS_DPR.issubset(cols):
        missing = REQUIRED_COLUMNS_DPR - cols
        if missing:
            raise ReportValidationError(
                code="MISSING_REQUIRED_COLUMNS",
                message=f"Spreadsheet missing required DPR columns: {sorted(list(missing))}",
                details={"missing_columns": sorted(list(missing)), "found_columns": sorted(list(cols))}
            )
    elif "discipline" in fname_lower or REQUIRED_COLUMNS_DISCIPLINE.issubset(cols):
        missing = REQUIRED_COLUMNS_DISCIPLINE - cols
        if missing:
            raise ReportValidationError(
                code="MISSING_REQUIRED_COLUMNS",
                message=f"Spreadsheet missing required Discipline Report columns: {sorted(list(missing))}",
                details={"missing_columns": sorted(list(missing)), "found_columns": sorted(list(cols))}
            )
