import io
import uuid
import datetime
import pandas as pd
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.db.models.report import SourceReport, ProcessingStatus
from backend.app.db.models.event import ExtractedEvent
from backend.app.services.text_segmenter import segment_text_into_events
from backend.app.services.field_extractors import (
    extract_status,
    extract_percent_complete,
    extract_identifier,
    extract_action,
    extract_object,
    extract_location,
    extract_quantity_and_unit,
    extract_explicit_date
)

class EventExtractionService:
    def __init__(self, db: Session):
        self.db = db

    def extract_events_from_report(self, report_id: str) -> Tuple[SourceReport, List[ExtractedEvent]]:
        """
        Orchestrates event extraction for a validated report.
        Idempotent: If events were already extracted, returns existing records.
        """
        report = self.db.query(SourceReport).filter(SourceReport.report_id == report_id).first()
        if not report:
            raise ValueError(f"Report with ID '{report_id}' not found.")

        # Idempotency check: if events already exist in DB, return them
        existing_events = self.db.query(ExtractedEvent).filter(ExtractedEvent.report_id == report_id).all()
        if existing_events:
            return report, existing_events

        events_to_create = []

        if report.source_type == "TXT":
            events_to_create = self._extract_from_txt(report)
        elif report.source_type in ("CSV", "XLSX"):
            events_to_create = self._extract_from_spreadsheet(report)

        # Store ExtractedEvent DB records
        created_events = []
        for event_data in events_to_create:
            evt_id = f"EVT-{datetime.datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:12].upper()}"
            evt = ExtractedEvent(
                event_id=evt_id,
                report_id=report.report_id,
                raw_text=event_data["raw_text"],
                event_date=event_data["event_date"],
                event_date_source=event_data["event_date_source"],
                discipline=event_data["discipline"],
                action=event_data["action"],
                object=event_data["object"],
                identifier=event_data["identifier"],
                location=event_data["location"],
                status=event_data["status"],
                percent_complete=event_data["percent_complete"],
                quantity=event_data["quantity"],
                unit=event_data["unit"],
                source_position=event_data["source_position"],
                extraction_method=event_data["extraction_method"],
                extraction_version="v1"
            )
            self.db.add(evt)
            created_events.append(evt)

        report.processing_status = ProcessingStatus.EVENTS_EXTRACTED.value
        self.db.commit()

        for evt in created_events:
            self.db.refresh(evt)

        return report, created_events

    def _extract_from_txt(self, report: SourceReport) -> List[Dict[str, Any]]:
        segments = segment_text_into_events(report.raw_content or "")
        events = []

        for seg in segments:
            text = seg["text"]
            
            action = extract_action(text)
            obj = extract_object(text)
            identifier = extract_identifier(text)
            location = extract_location(text)
            status = extract_status(text)
            percent_complete = extract_percent_complete(text)
            quantity, unit = extract_quantity_and_unit(text)
            explicit_date = extract_explicit_date(text)

            # Skip non-event lines (e.g. site safety meetings or greetings with no work evidence)
            if not any([action, identifier, status, percent_complete != None, location]):
                continue

            event_date = report.report_date
            event_date_source = "REPORT_DATE"
            if explicit_date:
                try:
                    event_date = pd.to_datetime(explicit_date).date()
                    event_date_source = "EXPLICIT"
                except Exception:
                    pass

            events.append({
                "raw_text": text,
                "event_date": event_date,
                "event_date_source": event_date_source,
                "discipline": report.discipline,
                "action": action,
                "object": obj,
                "identifier": identifier,
                "location": location,
                "status": status,
                "percent_complete": percent_complete,
                "quantity": quantity,
                "unit": unit,
                "source_position": seg["source_position"],
                "extraction_method": "RULE_BASED"
            })

        return events

    def _extract_from_spreadsheet(self, report: SourceReport) -> List[Dict[str, Any]]:
        events = []
        if report.source_type == "CSV":
            try:
                df = pd.read_csv(io.StringIO(report.raw_content or ""))
            except Exception as e:
                raise ValueError(f"Malformed CSV content could not be parsed: {str(e)}")
        elif report.source_type == "XLSX":
            try:
                import json
                parsed_records = json.loads(report.raw_content or "[]")
                if not isinstance(parsed_records, list):
                    raise ValueError("Serialized XLSX content must be a JSON array of row records.")
                df = pd.DataFrame(parsed_records)
            except Exception as e:
                raise ValueError(f"Malformed XLSX serialized JSON content could not be parsed: {str(e)}")
        else:
            return self._extract_from_txt(report)

        if df.empty:
            return events

        for loop_idx, (row_idx, row) in enumerate(df.iterrows()):
            row_dict = row.to_dict()
            
            # Combine text representation from row
            text_fragment = " ".join([str(v) for k, v in row_dict.items() if pd.notnull(v) and str(v).strip()])
            
            action = extract_action(text_fragment)
            obj = extract_object(text_fragment)
            identifier = extract_identifier(text_fragment) or str(row_dict.get("equipment_or_line_id", "")).strip() or None
            location = extract_location(text_fragment) or str(row_dict.get("location", "")).strip() or None
            
            status = str(row_dict.get("status", "")).strip() if pd.notnull(row_dict.get("status")) else extract_status(text_fragment)
            if status and status not in ("NOT_STARTED", "STARTED", "IN_PROGRESS", "COMPLETED"):
                status = extract_status(text_fragment)
            
            percent_complete = extract_percent_complete(text_fragment)
            if percent_complete is None and pd.notnull(row_dict.get("progress_percentage")):
                try:
                    pct_val = row_dict.get("progress_percentage")
                    pct = float(str(pct_val)) if pct_val is not None else 0.0
                    if 0.0 <= pct <= 100.0:
                        percent_complete = pct
                except ValueError:
                    pass

            quantity, unit = extract_quantity_and_unit(text_fragment)
            
            disc = str(row_dict.get("discipline", "")).strip() if pd.notnull(row_dict.get("discipline")) else report.discipline

            events.append({
                "raw_text": text_fragment,
                "event_date": report.report_date,
                "event_date_source": "REPORT_DATE",
                "discipline": disc or report.discipline,
                "action": action,
                "object": obj,
                "identifier": identifier,
                "location": location,
                "status": status,
                "percent_complete": percent_complete,
                "quantity": quantity,
                "unit": unit,
                "source_position": {
                    "type": f"{report.source_type}_ROW",
                    "row": loop_idx + 1
                },
                "extraction_method": "STRUCTURED_COLUMN_MAPPING"
            })

        return events
