import sys
from pathlib import Path

import pandas as pd


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python read_aql_excel.py <path_to_excel_file>")
        sys.exit(1)

    excel_path = Path(sys.argv[1])
    if not excel_path.exists():
        print(f"Error: File not found -> {excel_path}")
        sys.exit(1)

    try:
        xls = pd.ExcelFile(excel_path)
    except Exception as exc:
        print(f"Failed to open Excel file: {exc}")
        sys.exit(1)

    sheet_names = xls.sheet_names
    print("Sheets:", ", ".join(sheet_names))

    for sheet_name in sheet_names:
        print(f"\n=== Sheet: {sheet_name} ===")
        try:
            # Read as raw grid without header inference to preserve layout
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None, dtype=str)
        except Exception as exc:
            print(f"Error reading sheet '{sheet_name}': {exc}")
            continue

        # Replace NaN with empty strings for clearer display/export
        df = df.fillna("")

        # Save to workspace for reference
        safe_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in sheet_name)
        output_dir = Path("aql_output")
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{safe_name}.csv"
        try:
            df.to_csv(out_path, index=False, header=False)
        except Exception as exc:
            print(f"Warning: failed to save '{sheet_name}' to CSV: {exc}")

        # Print as CSV to stdout for untruncated display
        print(f"(saved: {out_path})")
        try:
            # to_csv to stdout ensures no truncation
            df.to_csv(sys.stdout, index=False, header=False)
        except Exception as exc:
            print(f"Warning: failed to print '{sheet_name}' as CSV: {exc}")


if __name__ == "__main__":
    main()


