"""
inspect_bcp.py
==============
Prints the raw hex and attempted text decoding of the first BCP chunk
for a few tables. Run this so we can figure out the binary format.

Usage:
    python inspect_bcp.py
"""

import zipfile
from collections import defaultdict

BACPAC_PATH = r"data\WideWorldImporters-Standard.bacpac"

z = zipfile.ZipFile(BACPAC_PATH, "r")
all_files = z.namelist()
bcp_files = [f for f in all_files if f.startswith("Data/") and f.endswith(".BCP")]

table_chunks = defaultdict(list)
for f in bcp_files:
    parts = f.split("/")
    if len(parts) == 3:
        table_chunks[parts[1]].append(f)
for tbl in table_chunks:
    table_chunks[tbl].sort()

# Inspect first chunk of first 3 tables
sample_tables = list(sorted(table_chunks.keys()))[:3]

for tbl in sample_tables:
    chunk_path = table_chunks[tbl][0]
    raw = z.read(chunk_path)
    print(f"\n{'='*60}")
    print(f"Table : {tbl}")
    print(f"Chunk : {chunk_path}")
    print(f"Size  : {len(raw)} bytes")
    print(f"\nFirst 300 bytes (hex):")
    for i in range(0, min(300, len(raw)), 16):
        hex_part = " ".join(f"{b:02x}" for b in raw[i:i+16])
        asc_part = "".join(chr(b) if 32 <= b < 127 else "." for b in raw[i:i+16])
        print(f"  {i:04x}  {hex_part:<48}  {asc_part}")

    print(f"\nTry UTF-16-LE decode (first 200 chars):")
    try:
        txt = raw[:400].decode("utf-16-le")
        print(repr(txt))
    except Exception as e:
        print(f"  FAILED: {e}")

    print(f"\nTry UTF-8 decode (first 200 chars):")
    try:
        txt = raw[:200].decode("utf-8")
        print(repr(txt))
    except Exception as e:
        print(f"  FAILED: {e}")

z.close()