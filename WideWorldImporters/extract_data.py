"""
export_csv.py
=============
Exports all WideWorldImporters tables to CSV.
geography/geometry columns are cast to WKT text via STAsText().
hierarchyid columns are cast to varchar via ToString().

Place inside WideWorldImporters/ and run:
    python export_csv.py
"""

import csv, os
import pyodbc

OUT_DIR = "csv"
os.makedirs(OUT_DIR, exist_ok=True)

# Clear old CSVs
for f in os.listdir(OUT_DIR):
    if f.endswith(".csv"):
        os.remove(os.path.join(OUT_DIR, f))
print("Cleared old CSVs.")

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=WideWorldImporters;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)
cursor      = conn.cursor()
meta_cursor = conn.cursor()

# SQL type codes for unsupported types
GEOGRAPHY_TYPES  = {-151}   # geography
GEOMETRY_TYPES   = {-150}   # geometry
HIERARCHYID_TYPES = {-152}  # hierarchyid

tables = cursor.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
      AND TABLE_NAME NOT LIKE '%Archive%'
    ORDER BY TABLE_SCHEMA, TABLE_NAME
""").fetchall()

print(f"Found {len(tables)} tables.\n")

# Also get column DATA_TYPE from INFORMATION_SCHEMA for accurate casting
def get_col_types(schema, table):
    """Returns dict: col_name -> data_type string"""
    rows = meta_cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
    """, schema, table).fetchall()
    return {r[0]: r[1].lower() for r in rows}

for schema, table in tables:
    col_types = get_col_types(schema, table)

    # Build SELECT casting special types
    select_parts = []
    for col, dtype in col_types.items():
        if dtype == "geography":
            select_parts.append(f"[{col}].STAsText() AS [{col}]")
        elif dtype == "geometry":
            select_parts.append(f"[{col}].STAsText() AS [{col}]")
        elif dtype == "hierarchyid":
            select_parts.append(f"CAST([{col}] AS VARCHAR(4000)) AS [{col}]")
        else:
            select_parts.append(f"[{col}]")

    col_select = ", ".join(select_parts)

    try:
        rows = cursor.execute(
            f"SELECT {col_select} FROM [{schema}].[{table}]"
        ).fetchall()
        col_names = list(col_types.keys())

        out_path = os.path.join(OUT_DIR, f"{table}.csv")
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(col_names)
            w.writerows(rows)

        print(f"  + {schema}.{table}: {len(rows)} rows, {len(col_names)} cols")

    except Exception as e:
        print(f"  ! ERROR {schema}.{table}: {e}")

conn.close()
print("\nDone.")