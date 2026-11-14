import sys
import json

from pathlib import Path

from src.log_parser import (
    group_errors,
    extract_error_contexts
)

from src.analyzer import analyze_error

from src.database import (
    initialize_database,
    save_scan_results
)

def run_bug_finder(log_file_path: str):

    log_file = Path(log_file_path)

    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return

    # Initialize database
    initialize_database()

    # Read logs
    log_text = log_file.read_text(
        encoding="utf-8",
        errors="replace"
    )

    # Group similar errors
    error_groups = group_errors(log_text)

    if not error_groups:
        print("No errors found in the provided logs.")
        return

    print(f"\nFound {len(error_groups)} unique error group(s).")

    # Extract contexts only once
    contexts = extract_error_contexts(log_text)

    scan_results = []

    for index, group in enumerate(error_groups, start=1):

        print(f"\n{'=' * 60}")
        print(f"BUG ANALYSIS #{index}")
        print(f"{'=' * 60}")

        print(f"Occurrences : {group['count']}")
        print(f"Severity    : {group['severity']}")
        print(f"First Seen  : {group['first_seen']}")
        print(f"Last Seen   : {group['last_seen']}")

        matching_context = None

        for context in contexts:

            if any(
                example in context
                for example in group["examples"]
            ):
                matching_context = context
                break

        if matching_context is None:
            matching_context = "\n".join(group["examples"])

        # Build a result even if AI analysis fails
        result = {
            **group,
            "ai_analysis": None,
            "analysis_status": "FAILED",
            "analysis_error": None
        }

        try:

            analysis = analyze_error(matching_context)

            result["ai_analysis"] = analysis.model_dump()
            result["analysis_status"] = "SUCCESS"

            print(json.dumps(
                result["ai_analysis"],
                indent=2
            ))

        except Exception as e:

            result["analysis_error"] = str(e)

            print(f"Analysis failed: {e}")

        scan_results.append(result)

    # Save all groups, including failed AI analyses
    scan_id = save_scan_results(
        source_file=log_file.name,
        results=scan_results
    )

    # Build unified JSON report
    successful_analyses = sum(
        1 for item in scan_results
        if item["analysis_status"] == "SUCCESS"
    )

    report = {
        "scan_id": scan_id,
        "source_file": log_file.name,
        "total_unique_error_groups": len(error_groups),
        "total_error_occurrences": sum(
            group["count"] for group in error_groups
        ),
        "successful_analyses": successful_analyses,
        "analyses": scan_results
    }

    report_path = log_file.with_name(
        f"{log_file.stem}_bug_report.json"
    )

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\n" + "=" * 60)
    print("BUG FINDER SCAN COMPLETED")
    print("=" * 60)

    print(f"Scan ID             : {scan_id}")
    print(f"Unique error groups : {len(error_groups)}")
    print(f"Successful analyses : {successful_analyses}")
    print(f"Database            : bug_finder.db")
    print(f"JSON report         : {report_path}")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python -m src.main <log_file_path>")
    else:
        run_bug_finder(sys.argv[1])


#------------------Without error fingerprinting-----------------------------

# import sys
# import json
# from pathlib import Path
# from src.log_parser import extract_error_contexts
# from src.analyzer import analyze_error

# def run_bug_finder(log_file_path: str):

#     log_file = Path(log_file_path)

#     # Step 1: Check file existence
#     if not log_file.exists():
#         print(f"Log file not found: {log_file}")
#         return

#     # Step 2: Read log file
#     log_text = log_file.read_text(
#         encoding="utf-8",
#         errors="replace"
#     )

#     # Step 3: Extract error contexts
#     error_contexts = extract_error_contexts(log_text)

#     if not error_contexts:
#         print("No errors found in the provided logs.")
#         return

#     print(f"Found {len(error_contexts)} error context(s).")

#     analyses = []

#     # Step 4: Analyze each context
#     for index, context in enumerate(error_contexts, start=1):

#         print(f"\n{'=' * 50}")
#         print(f"BUG ANALYSIS #{index}")
#         print(f"{'=' * 50}")

#         try:
#             analysis = analyze_error(context)

#             result = analysis.model_dump()    #convert Pydantic object to Python dictionary
#             analyses.append(result)

#             print(json.dumps(result, indent=2))

#         except Exception as e:
#             print(f"Analysis failed: {e}")

#     # Step 5: Save report
#     if analyses:

#         report = {
#             "source_file": log_file.name,
#             "total_error_contexts": len(error_contexts),
#             "successful_analyses": len(analyses),
#             "analyses": analyses
#         }

#         report_path = log_file.with_name(
#             f"{log_file.stem}_bug_report.json"
#         )

#         with open(report_path, "w", encoding="utf-8") as file:
#             json.dump(report, file, indent=4)

#         print(f"\nBug report saved at: {report_path}")


# if __name__ == "__main__":

#     if len(sys.argv) < 2:
#         print("Usage: python -m src.main <log_file_path>")
#     else:
#         run_bug_finder(sys.argv[1])

#------------------------------------------------------------------------
#without saving in file -

# import sys
# from pathlib import Path
# from src.log_parser import extract_error_contexts
# from src.analyzer import analyze_error

# def run_bug_finder(log_file_path: str):

#     log_file = Path(log_file_path)

#     # Step 1: Check whether file exists
#     if not log_file.exists():
#         print(f"Log file not found: {log_file}")
#         return

#     # Step 2: Read log file
#     log_text = log_file.read_text(encoding="utf-8", errors="replace")

#     # Step 3: Extract error contexts
#     error_contexts = extract_error_contexts(log_text)

#     if not error_contexts:
#         print("No errors found in the provided logs.")
#         return

#     print(f"Found {len(error_contexts)} error context(s).")

#     # Step 4: Analyze each error context
#     for index, context in enumerate(error_contexts, start=1):

#         print(f"\n{'=' * 50}")
#         print(f"BUG ANALYSIS #{index}")
#         print(f"{'=' * 50}")

#         try:
#             analysis = analyze_error(context)
#             print(analysis.model_dump_json(indent=2))

#         except Exception as e:
#             print(f"Analysis failed: {e}")


# if __name__ == "__main__":

#     if len(sys.argv) < 2:
#         print("Usage: python -m src.main <log_file_path>")
#     else:
#         run_bug_finder(sys.argv[1])

# #python -m src.main sample_logs/application.log  we can run like this in terminal which means 
