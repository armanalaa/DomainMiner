import re
import os

# Paths relative to the Employees root folder (where this script lives)
CSV_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "csv")


def extract_row_values(line):
    """
    Extracts values from SQL-style rows in two formats:
      - INSERT INTO `table` VALUES (v1,'v2','v3'),
      - (v1,'v2','v3'),
    Returns a list of string values, or None if no match.
    """
    # Strip surrounding quotes added by Excel/CSV wrapping
    line = line.strip().strip('"')

    # Format 1: INSERT INTO `table` VALUES (...)
    m = re.match(r"INSERT INTO\s+`?\w+`?\s+VALUES\s+\((.*)\)[,;]?$", line, re.IGNORECASE)
    if not m:
        # Format 2: plain (...)
        m = re.match(r"^\((.*)\)[,;]?$", line)
    if not m:
        return None

    content = m.group(1)
    # Extract all values: quoted strings or unquoted numbers
    values = re.findall(r"'([^']*)'|(-?\d[\d.]*)", content)
    return [q if q != "" else u for q, u in values]


def is_sql_format(lines):
    """Check if any of the first few data lines look like SQL INSERT rows."""
    for line in lines[1:6]:
        clean = line.strip().strip('"')
        if re.match(r"INSERT INTO", clean, re.IGNORECASE) or re.match(r"^\(", clean):
            return True
    return False


def fix_csv_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if len(lines) < 2:
        print(f"  [SKIP] {os.path.basename(filepath)} — too few lines")
        return

    header = lines[0].strip()

    if not is_sql_format(lines):
        print(f"  [SKIP] {os.path.basename(filepath)} — already clean CSV")
        return

    columns = [c.strip() for c in header.split(",")]
    num_cols = len(columns)

    fixed_lines = [header]
    skipped = 0

    for line in lines[1:]:
        row = extract_row_values(line)
        if row is None:
            skipped += 1
            continue
        if len(row) == num_cols:
            fixed_lines.append(",".join(row))
        else:
            skipped += 1

    with open(filepath, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(fixed_lines) + "\n")

    print(f"  [FIXED] {os.path.basename(filepath)} — "
          f"{len(fixed_lines) - 1} rows written, {skipped} skipped")


def main():
    if not os.path.isdir(CSV_FOLDER):
        print(f"ERROR: csv folder not found at: {CSV_FOLDER}")
        return

    csv_files = [f for f in os.listdir(CSV_FOLDER) if f.lower().endswith(".csv")]

    if not csv_files:
        print("No CSV files found in the csv folder.")
        return

    print(f"Found {len(csv_files)} CSV file(s) in: {CSV_FOLDER}\n")

    for filename in sorted(csv_files):
        filepath = os.path.join(CSV_FOLDER, filename)
        fix_csv_file(filepath)

    print("\nDone.")


if __name__ == "__main__":
    main()