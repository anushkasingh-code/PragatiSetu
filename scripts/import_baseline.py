import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.db.database import SessionLocal, Base, engine
from backend.app.services.baseline_importer import BaselineImporter

def main():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    excel_path = os.path.join(PROJECT_ROOT, "dataset", "01_baseline_schedule.xlsx")
    print(f"Importing baseline schedule from: {excel_path}")

    db = SessionLocal()
    try:
        importer = BaselineImporter(db)
        stats = importer.import_excel_baseline(excel_path)
        print("\n--- Import Summary ---")
        print(f"File: {stats['file_path']}")
        print(f"Sheets Found: {stats['sheets_found']}")
        print(f"Projects Imported: {stats['projects_imported']}")
        print(f"WBS Nodes Imported: {stats['wbs_nodes_imported']}")
        print(f"Activities Imported: {stats['activities_imported']}")
        
        if stats['activities_imported'] == 75:
            print("\n[VERIFIED] Project Alpha imported activity count matches expected ground truth: 75 activities!")
        else:
            print(f"\n[WARNING] Project Alpha activity count ({stats['activities_imported']}) differs from expected 75!")

    except Exception as e:
        print(f"\n[ERROR] Baseline import failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
