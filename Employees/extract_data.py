"""
generate_csv.py
===============
Converts MySQL Employees .dump files (tab-delimited) to CSV files.
Place inside Employees/ and run:
    python generate_csv.py
"""

import csv, os
from pathlib import Path

SRC_DIR = Path("test_db")
OUT_DIR = Path("csv")
OUT_DIR.mkdir(exist_ok=True)

# Map: output CSV name -> (dump file(s), column headers)
tables = {
    "departments": (
        ["load_departments.dump"],
        ["dept_no", "dept_name"]
    ),
    "employees": (
        ["load_employees.dump"],
        ["emp_no", "birth_date", "first_name", "last_name", "gender", "hire_date"]
    ),
    "dept_emp": (
        ["load_dept_emp.dump"],
        ["emp_no", "dept_no", "from_date", "to_date"]
    ),
    "dept_manager": (
        ["load_dept_manager.dump"],
        ["emp_no", "dept_no", "from_date", "to_date"]
    ),
    "salaries": (
        ["load_salaries1.dump", "load_salaries2.dump", "load_salaries3.dump"],
        ["emp_no", "salary", "from_date", "to_date"]
    ),
    "titles": (
        ["load_titles.dump"],
        ["emp_no", "title", "from_date", "to_date"]
    ),
}

print(f"Reading from : {SRC_DIR.resolve()}")
print(f"Writing to   : {OUT_DIR.resolve()}\n")

for table, (dump_files, headers) in tables.items():
    out_path = OUT_DIR / f"{table}.csv"
    row_count = 0

    with open(out_path, "w", newline="", encoding="utf-8") as fout:
        writer = csv.writer(fout)
        writer.writerow(headers)

        for dump_file in dump_files:
            dump_path = SRC_DIR / dump_file
            if not dump_path.exists():
                print(f"  ! {dump_file} not found — skipping")
                continue
            with open(dump_path, "r", encoding="utf-8", errors="replace") as fin:
                for line in fin:
                    line = line.rstrip("\n\r")
                    if not line:
                        continue
                    fields = line.split("\t")
                    writer.writerow(fields)
                    row_count += 1

    print(f"  + {table}: {row_count} rows, {len(headers)} cols -> {out_path.name}")

print("\nDone.")