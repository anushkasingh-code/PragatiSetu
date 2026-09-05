import os
import logging
import datetime
import pandas as pd
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.db.models.project import Project
from backend.app.db.models.wbs import WBSNode
from backend.app.db.models.activity import ScheduleActivity
from backend.app.services.validation import (
    validate_date_range,
    validate_percent_complete,
    validate_status,
    validate_duplicate_activity_ids,
    ValidationError
)
from backend.app.services.ai.vector_indexer import index_schedule_activities
from backend.app.services.normalizer_service import normalize_project_id

def _normalize_project_id(pid: Any) -> str:
    return normalize_project_id(str(pid) if pid is not None else None)


class BaselineImporter:
    def __init__(self, db_session: Session):
        self.db = db_session

    def import_excel_baseline(self, file_path: str, target_project_id: Optional[str] = None) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Baseline schedule file not found at: {file_path}")

        target_proj_norm = _normalize_project_id(target_project_id) if target_project_id else None

        excel_file = pd.ExcelFile(file_path)
        sheets = excel_file.sheet_names

        stats = {
            "file_path": file_path,
            "sheets_found": sheets,
            "projects_imported": 0,
            "wbs_nodes_imported": 0,
            "activities_imported": 0,
            "errors": []
        }

        # 1. Read Project sheet or Baseline sheet
        if "Project" in sheets:
            df_proj = pd.read_excel(file_path, sheet_name="Project")
            for _, row in df_proj.iterrows():
                row_dict = row.to_dict()
                raw_sheet_proj = row_dict.get("project_id")
                sheet_proj_id = _normalize_project_id(raw_sheet_proj) if pd.notnull(raw_sheet_proj) and str(raw_sheet_proj).strip() else None
                if target_proj_norm and sheet_proj_id and sheet_proj_id != target_proj_norm:
                    raise ValueError(f"Project ID mismatch: Spreadsheet specifies '{sheet_proj_id}' but endpoint target is '{target_proj_norm}'.")
                proj_id = target_proj_norm or (sheet_proj_id if sheet_proj_id else "PROJ-ALPHA")
                proj_name = str(row_dict.get("name", f"Project {proj_id}")).strip()
                proj_desc = str(row_dict["description"]) if pd.notnull(row_dict.get("description")) else None
                
                existing_proj = self.db.query(Project).filter(Project.project_id == proj_id).first()
                if not existing_proj:
                    proj = Project(
                        project_id=proj_id,
                        name=proj_name,
                        description=proj_desc
                    )
                    self.db.add(proj)
                else:
                    existing_proj.name = proj_name
                    existing_proj.description = proj_desc
                stats["projects_imported"] += 1
        elif "Baseline" in sheets:
            df_base = pd.read_excel(file_path, sheet_name="Baseline")
            df_base_projs = df_base[["project_id", "project_name"]].copy() if "project_name" in df_base.columns else df_base[["project_id"]].copy()
            if "project_name" not in df_base_projs.columns:
                df_base_projs["project_name"] = df_base_projs["project_id"]
            df_base_projs["norm_proj_id"] = df_base_projs["project_id"].apply(_normalize_project_id)
            unique_projs = df_base_projs[["norm_proj_id", "project_name"]].drop_duplicates()
            for _, row in unique_projs.iterrows():
                row_dict = row.to_dict()
                sheet_proj_id = str(row_dict["norm_proj_id"]).strip()
                if target_proj_norm and sheet_proj_id and sheet_proj_id != target_proj_norm:
                    raise ValueError(f"Project ID mismatch: Spreadsheet specifies '{sheet_proj_id}' but endpoint target is '{target_proj_norm}'.")
                proj_id = target_proj_norm or sheet_proj_id
                proj_name = str(row_dict["project_name"]).strip()
                existing_proj = self.db.query(Project).filter(Project.project_id == proj_id).first()
                if not existing_proj:
                    proj = Project(project_id=proj_id, name=proj_name, description=f"{proj_name} Baseline Project")
                    self.db.add(proj)
                else:
                    existing_proj.name = proj_name
                    existing_proj.description = f"{proj_name} Baseline Project"
                stats["projects_imported"] += 1
        elif target_proj_norm:
            existing_proj = self.db.query(Project).filter(Project.project_id == target_proj_norm).first()
            if not existing_proj:
                proj = Project(project_id=target_proj_norm, name=f"Project {target_proj_norm}", description=f"{target_proj_norm} Baseline Project")
                self.db.add(proj)
                stats["projects_imported"] += 1

        self.db.flush()

        # 2. Read WBS_Nodes sheet or Baseline sheet
        if "WBS_Nodes" in sheets:
            df_wbs = pd.read_excel(file_path, sheet_name="WBS_Nodes")
            # Sort WBS nodes by level to respect parent hierarchy insertion
            if "level" in df_wbs.columns:
                df_wbs = df_wbs.sort_values(by="level")

            for _, row in df_wbs.iterrows():
                row_dict = row.to_dict()
                wbs_id = str(row_dict["wbs_id"]).strip()
                raw_wbs_proj = row_dict.get("project_id")
                sheet_proj = _normalize_project_id(raw_wbs_proj) if pd.notnull(raw_wbs_proj) and str(raw_wbs_proj).strip() else None
                if target_proj_norm and sheet_proj and sheet_proj != target_proj_norm:
                    raise ValueError(f"Project ID mismatch in WBS: Spreadsheet specifies '{sheet_proj}' but endpoint target is '{target_proj_norm}'.")
                proj_id = target_proj_norm or (sheet_proj if sheet_proj else "PROJ-ALPHA")
                parent_id = str(row_dict["parent_wbs_id"]).strip() if pd.notnull(row_dict.get("parent_wbs_id")) and str(row_dict.get("parent_wbs_id")).strip() != "None" else None
                level = int(float(str(row_dict["level"])))
                name = str(row_dict["name"]).strip()

                existing_wbs = self.db.query(WBSNode).filter(WBSNode.wbs_id == wbs_id).first()
                if not existing_wbs:
                    wbs = WBSNode(
                        wbs_id=wbs_id,
                        project_id=proj_id,
                        parent_wbs_id=parent_id,
                        level=level,
                        name=name
                    )
                    self.db.add(wbs)
                else:
                    existing_wbs.project_id = proj_id
                    existing_wbs.name = name
                    existing_wbs.level = level
                    existing_wbs.parent_wbs_id = parent_id
                stats["wbs_nodes_imported"] += 1
        elif "Baseline" in sheets:
            df_base = pd.read_excel(file_path, sheet_name="Baseline")
            # Extract WBS nodes from wbs_level_1, wbs_level_2, wbs_level_3 columns
            wbs_nodes_seen = set()
            for _, row in df_base.iterrows():
                row_dict = row.to_dict()
                raw_wbs_proj = row_dict.get("project_id")
                sheet_proj = _normalize_project_id(raw_wbs_proj) if pd.notnull(raw_wbs_proj) and str(raw_wbs_proj).strip() else None
                if target_proj_norm and sheet_proj and sheet_proj != target_proj_norm:
                    raise ValueError(f"Project ID mismatch in WBS: Spreadsheet specifies '{sheet_proj}' but endpoint target is '{target_proj_norm}'.")
                proj_id = target_proj_norm or (sheet_proj if sheet_proj else "PROJ-ALPHA")
                l1 = str(row_dict["wbs_level_1"]).strip() if pd.notnull(row_dict.get("wbs_level_1")) else None
                l2 = str(row_dict["wbs_level_2"]).strip() if pd.notnull(row_dict.get("wbs_level_2")) else None
                l3 = str(row_dict["wbs_level_3"]).strip() if pd.notnull(row_dict.get("wbs_level_3")) else None

                if l1 and l1 not in wbs_nodes_seen:
                    wbs_nodes_seen.add(l1)
                    if not self.db.query(WBSNode).filter(WBSNode.wbs_id == l1).first():
                        self.db.add(WBSNode(wbs_id=l1, project_id=proj_id, level=1, name=l1))
                    stats["wbs_nodes_imported"] += 1
                if l2 and l2 not in wbs_nodes_seen:
                    wbs_nodes_seen.add(l2)
                    if not self.db.query(WBSNode).filter(WBSNode.wbs_id == l2).first():
                        self.db.add(WBSNode(wbs_id=l2, project_id=proj_id, parent_wbs_id=l1, level=2, name=l2))
                    stats["wbs_nodes_imported"] += 1
                if l3 and l3 not in wbs_nodes_seen:
                    wbs_nodes_seen.add(l3)
                    if not self.db.query(WBSNode).filter(WBSNode.wbs_id == l3).first():
                        self.db.add(WBSNode(wbs_id=l3, project_id=proj_id, parent_wbs_id=l2, level=3, name=l3))
                    stats["wbs_nodes_imported"] += 1

        self.db.flush()

        # 3. Read Activities sheet or Baseline sheet
        if "Activities" in sheets or "Baseline" in sheets:
            sheet_name = "Activities" if "Activities" in sheets else "Baseline"
            df_act = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Check duplicate activity IDs in file
            act_ids = [str(r).strip() for r in df_act["activity_id"].dropna()]
            validate_duplicate_activity_ids(act_ids)

            for _, row in df_act.iterrows():
                row_dict = row.to_dict()
                act_id = str(row_dict["activity_id"]).strip()
                raw_act_proj = row_dict.get("project_id")
                sheet_proj = _normalize_project_id(raw_act_proj) if pd.notnull(raw_act_proj) and str(raw_act_proj).strip() else None
                if target_proj_norm and sheet_proj and sheet_proj != target_proj_norm:
                    raise ValueError(f"Project ID mismatch in Activity '{act_id}': Spreadsheet specifies '{sheet_proj}' but endpoint target is '{target_proj_norm}'.")
                proj_id = target_proj_norm or (sheet_proj if sheet_proj else "PROJ-ALPHA")
                
                # Handle wbs_id
                wbs_id = None
                if pd.notnull(row_dict.get("wbs_id")):
                    wbs_id = str(row_dict.get("wbs_id")).strip()
                elif pd.notnull(row_dict.get("wbs_level_3")):
                    wbs_id = str(row_dict.get("wbs_level_3")).strip()
                elif pd.notnull(row_dict.get("wbs_level_2")):
                    wbs_id = str(row_dict.get("wbs_level_2")).strip()

                discipline = str(row_dict["discipline"]).strip()
                desc_col = "activity_description" if "activity_description" in row_dict else "description"
                description = str(row_dict[desc_col]).strip()
                location = str(row_dict["location"]).strip() if pd.notnull(row_dict.get("location")) else None
                eq_line_id = str(row_dict["equipment_or_line_id"]).strip() if pd.notnull(row_dict.get("equipment_or_line_id")) else None
                
                # Parse dates
                p_start = pd.to_datetime(row_dict["planned_start"]).date()
                p_finish = pd.to_datetime(row_dict["planned_finish"]).date()

                # Validate planned dates
                validate_date_range(p_start, p_finish)

                # Parse actuals & validation
                pct_col = "planned_percent_complete" if "planned_percent_complete" in row_dict else "percent_complete"
                pct_val = row_dict.get(pct_col, 0.0)
                pct = float(str(pct_val)) if pd.notnull(pct_val) else 0.0
                if pd.isna(pct):
                    pct = 0.0
                validate_percent_complete(pct)

                status_col = "baseline_status" if "baseline_status" in row_dict else "status"
                status = str(row_dict.get(status_col, "NOT_STARTED")).strip()
                if status not in ("NOT_STARTED", "STARTED", "IN_PROGRESS", "COMPLETED"):
                    status = "NOT_STARTED"
                validate_status(status)

                pred_id = str(row_dict.get("predecessor_activity_id")).strip() if pd.notnull(row_dict.get("predecessor_activity_id")) and str(row_dict.get("predecessor_activity_id")).strip() not in ("None", "nan") else None

                existing_act = self.db.query(ScheduleActivity).filter(ScheduleActivity.activity_id == act_id).first()
                if not existing_act:
                    act = ScheduleActivity(
                        activity_id=act_id,
                        project_id=proj_id,
                        wbs_id=wbs_id,
                        discipline=discipline,
                        description=description,
                        location=location,
                        equipment_or_line_id=eq_line_id,
                        planned_start=p_start,
                        planned_finish=p_finish,
                        percent_complete=pct,
                        status=status,
                        predecessor_activity_id=pred_id
                    )
                    self.db.add(act)
                else:
                    existing_act.wbs_id = wbs_id
                    existing_act.discipline = discipline
                    existing_act.description = description
                    existing_act.location = location
                    existing_act.equipment_or_line_id = eq_line_id
                    existing_act.planned_start = p_start
                    existing_act.planned_finish = p_finish
                    existing_act.percent_complete = pct
                    existing_act.status = status
                    existing_act.predecessor_activity_id = pred_id

                stats["activities_imported"] += 1

        self.db.commit()
        
        # Ensure ChromaDB index is up to date with the imported activities
        try:
            index_schedule_activities(self.db)
        except Exception as e:
            logging.getLogger("pragatisetu.baseline_importer").error(
                "Chroma indexing failed during baseline import. The deterministic fallback will be used.", 
                exc_info=True
            )
            stats["errors"].append(f"Failed to index activities into ChromaDB: {str(e)}")
            
        return stats
