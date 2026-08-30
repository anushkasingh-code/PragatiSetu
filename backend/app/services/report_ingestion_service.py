import uuid
import datetime
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.db.models.project import Project
from backend.app.db.models.report import SourceReport, ProcessingStatus
from backend.app.services.hash_service import calculate_sha256
from backend.app.services.storage_service import save_uploaded_file, delete_uploaded_file
from backend.app.services.file_validator import (
    validate_file_content,
    validate_report_date,
    validate_discipline,
    ReportValidationError
)

class ReportIngestionService:
    def __init__(self, db: Session):
        self.db = db

    def ingest_report(
        self,
        project_id: str,
        filename: str,
        content: bytes,
        report_date_input: Any,
        discipline_input: str | None = None
    ) -> Tuple[bool, Dict[str, Any], SourceReport]:
        """
        Orchestrates full report validation, duplicate checking, local storage, and database persistence.
        Returns tuple: (is_duplicate: bool, result_dict: dict, report: SourceReport)
        """
        # 1. Verify Project Existence
        project = self.db.query(Project).filter(Project.project_id == project_id).first()
        if not project:
            raise ReportValidationError(
                code="INVALID_PROJECT",
                message=f"Project with ID '{project_id}' does not exist.",
                details={"project_id": project_id}
            )

        # 2. Validate Metadata (date, discipline)
        parsed_date = validate_report_date(report_date_input)
        parsed_discipline = validate_discipline(discipline_input)

        # 3. Validate File Content & Structure
        source_type, raw_content_str, _ = validate_file_content(filename, content)

        # 4. Calculate SHA-256 Hash
        file_hash = calculate_sha256(content)

        # 5. Check Duplicate File Hash within Project
        existing_report = self.db.query(SourceReport).filter(
            SourceReport.project_id == project_id,
            SourceReport.file_hash == file_hash
        ).first()

        if existing_report:
            # Duplicate file detected! Return existing report without creating new record
            result_payload = {
                "report_id": existing_report.report_id,
                "project_id": existing_report.project_id,
                "filename": existing_report.filename,
                "source_type": existing_report.source_type,
                "report_date": str(existing_report.report_date),
                "discipline": existing_report.discipline,
                "processing_status": existing_report.processing_status,
                "file_hash": existing_report.file_hash,
                "duplicate": True,
                "validation": {
                    "valid": False,
                    "errors": [
                        {
                            "code": "DUPLICATE_FILE",
                            "message": f"Duplicate report file detected. This exact file content was already uploaded as report '{existing_report.report_id}'."
                        }
                    ],
                    "warnings": []
                }
            }
            return True, result_payload, existing_report

        # 6. Store File locally on Disk
        stored_path = save_uploaded_file(filename, content)

        # 7. Create SourceReport Record
        report_id = f"REP-{datetime.datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        new_report = SourceReport(
            report_id=report_id,
            project_id=project_id,
            filename=filename,
            source_type=source_type,
            report_date=parsed_date,
            discipline=parsed_discipline,
            raw_content=raw_content_str,
            file_hash=file_hash,
            file_size=len(content),
            stored_path=stored_path,
            processing_status=ProcessingStatus.VALIDATED.value,
            rejection_reason=None
        )

        try:
            self.db.add(new_report)
            self.db.commit()
            self.db.refresh(new_report)
        except Exception as e:
            self.db.rollback()
            delete_uploaded_file(stored_path)
            raise RuntimeError(f"Database error while saving report record: {str(e)}") from e

        result_payload = {
            "report_id": new_report.report_id,
            "project_id": new_report.project_id,
            "filename": new_report.filename,
            "source_type": new_report.source_type,
            "report_date": str(new_report.report_date),
            "discipline": new_report.discipline,
            "processing_status": new_report.processing_status,
            "file_hash": new_report.file_hash,
            "duplicate": False,
            "validation": {
                "valid": True,
                "errors": [],
                "warnings": []
            }
        }

        return False, result_payload, new_report
