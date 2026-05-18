import duckdb, os, pandas as pd

out_dir = r"C:\Users\alaar\Desktop\Sapienza\CAISe2025_Revised\DL-To-DM\python\DomainMiner\TPC-H\csv"
os.makedirs(out_dir, exist_ok=True)

con = duckdb.connect()
con.execute("INSTALL tpch; LOAD tpch;")
con.execute("CALL dbgen(sf=0.01);")

tables = ["customer","orders","lineitem","part",
          "supplier","partsupp","nation","region"]

for t in tables:
    df = con.execute(f"SELECT * FROM {t}").df()
    df.to_csv(f"{out_dir}\\{t}.csv", index=False)
    print(f"{t}: {len(df)} rows, {len(df.columns)} cols")