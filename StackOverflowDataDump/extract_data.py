"""
extract_data.py  —  Stack Exchange / Stack Overflow
=====================================================
Extracts a Stack Exchange data dump (.7z) and converts all XML
tables to CSV files ready for the DomainMiner pipeline.

Stack Exchange data dump schema (8 XML files → 12 tables):
  From dump  : Posts, Users, Votes, Comments, Badges, Tags,
               PostHistory, PostLinks
  Generated  : PostTypes, VoteTypes, PostHistoryTypes, LinkTypes
               (lookup tables derived from documentation)

Download the dump manually from your Stack Exchange account:
  stackoverflow.com → Settings → Data Dump

Or use a smaller site for testing (faster):
  cooking.stackexchange.com, askubuntu.com, etc.
  (same schema, much smaller files)

Usage:
    cd StackOverflow
    python extract_data.py --dump stackoverflow.com.7z
    python extract_data.py --dump cooking.stackexchange.com.7z
    python extract_data.py --xml_dir xml/   # skip extraction, XML already unpacked

Output:
    StackOverflow/csv/<TableName>.csv

Requirements:
    pip install py7zr
"""

from __future__ import annotations

import argparse
import csv
import logging
import time
import xml.etree.ElementTree as ET
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# =============================================================================
# Table definitions — column order matches Stack Exchange schema documentation
# https://meta.stackexchange.com/questions/2677/
# =============================================================================

TABLES = {
    "Posts": [
        "Id", "PostTypeId", "AcceptedAnswerId", "ParentId",
        "CreationDate", "DeletionDate", "Score", "ViewCount",
        "Body", "OwnerUserId", "OwnerDisplayName", "LastEditorUserId",
        "LastEditorDisplayName", "LastEditDate", "LastActivityDate",
        "Title", "Tags", "AnswerCount", "CommentCount", "FavoriteCount",
        "ClosedDate", "CommunityOwnedDate", "ContentLicense",
    ],
    "Users": [
        "Id", "Reputation", "CreationDate", "DisplayName", "LastAccessDate",
        "WebsiteUrl", "Location", "AboutMe", "Views", "UpVotes", "DownVotes",
        "ProfileImageUrl", "EmailHash", "AccountId",
    ],
    "Votes": [
        "Id", "PostId", "VoteTypeId", "UserId", "CreationDate",
        "BountyAmount",
    ],
    "Comments": [
        "Id", "PostId", "Score", "Text", "CreationDate",
        "UserDisplayName", "UserId", "ContentLicense",
    ],
    "Badges": [
        "Id", "UserId", "Name", "Date", "Class", "TagBased",
    ],
    "Tags": [
        "Id", "TagName", "Count", "ExcerptPostId", "WikiPostId",
        "IsModeratorOnly", "IsRequired",
    ],
    "PostHistory": [
        "Id", "PostHistoryTypeId", "PostId", "RevisionGUID", "CreationDate",
        "UserId", "UserDisplayName", "Comment", "Text", "ContentLicense",
    ],
    "PostLinks": [
        "Id", "CreationDate", "PostId", "RelatedPostId", "LinkTypeId",
    ],
}

# Lookup tables generated from documentation (not in the dump XML)
LOOKUP_TABLES = {
    "PostTypes": [
        ("Id", "Name"),
        ("1",  "Question"),
        ("2",  "Answer"),
        ("3",  "Wiki"),
        ("4",  "TagWikiExcerpt"),
        ("5",  "TagWiki"),
        ("6",  "ModeratorNomination"),
        ("7",  "WikiPlaceholder"),
        ("8",  "PrivilegeWiki"),
    ],
    "VoteTypes": [
        ("Id", "Name"),
        ("1",  "AcceptedByOriginator"),
        ("2",  "UpMod"),
        ("3",  "DownMod"),
        ("4",  "Offensive"),
        ("5",  "Favorite"),
        ("6",  "Close"),
        ("7",  "Reopen"),
        ("8",  "BountyStart"),
        ("9",  "BountyClose"),
        ("10", "Deletion"),
        ("11", "Undeletion"),
        ("12", "Spam"),
        ("15", "ModeratorReview"),
        ("16", "ApproveEditSuggestion"),
    ],
    "PostHistoryTypes": [
        ("Id", "Name"),
        ("1",  "Initial Title"),
        ("2",  "Initial Body"),
        ("3",  "Initial Tags"),
        ("4",  "Edit Title"),
        ("5",  "Edit Body"),
        ("6",  "Edit Tags"),
        ("7",  "Rollback Title"),
        ("8",  "Rollback Body"),
        ("9",  "Rollback Tags"),
        ("10", "Post Closed"),
        ("11", "Post Reopened"),
        ("12", "Post Deleted"),
        ("13", "Post Undeleted"),
        ("14", "Post Locked"),
        ("15", "Post Unlocked"),
        ("16", "Community Owned"),
        ("17", "Post Migrated"),
        ("18", "Question Merged"),
        ("19", "Question Protected"),
        ("20", "Question Unprotected"),
        ("22", "Question Unmerged"),
        ("24", "Suggested Edit Applied"),
        ("25", "Post Tweeted"),
        ("31", "Discussion moved to chat"),
        ("33", "Post Notice Added"),
        ("34", "Post Notice Removed"),
        ("35", "Post Migrated Away"),
        ("36", "Post Migrated Here"),
        ("37", "Post Merge Source"),
        ("38", "Post Merge Destination"),
        ("50", "CommunityBump"),
        ("52", "Question Answered (Answered Removed)"),
    ],
    "LinkTypes": [
        ("Id", "Name"),
        ("1",  "Linked"),
        ("3",  "Duplicate"),
    ],
}


# =============================================================================
# Extraction
# =============================================================================

def extract_7z(archive_path: Path, xml_dir: Path) -> None:
    try:
        import py7zr
    except ImportError:
        raise ImportError("Run: pip install py7zr")

    xml_dir.mkdir(parents=True, exist_ok=True)
    log.info("Extracting %s → %s ...", archive_path.name, xml_dir)
    t0 = time.time()
    with py7zr.SevenZipFile(archive_path, mode="r") as z:
        z.extractall(path=xml_dir)
    log.info("Extracted in %.1fs", round(time.time() - t0, 1))


# =============================================================================
# XML → CSV (streaming, memory-efficient)
# =============================================================================

def xml_to_csv(xml_path: Path, csv_path: Path, columns: list[str]) -> int:
    """
    Parse a Stack Exchange XML file iteratively and write to CSV.
    Each <row> element's attributes become CSV columns.
    Uses iterparse for memory efficiency on large files (Posts.xml > 100 GB).
    """
    col_set   = set(columns)
    row_count = 0
    t0        = time.time()

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=columns,
            extrasaction="ignore",
            quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()

        context = ET.iterparse(str(xml_path), events=("end",))
        for event, elem in context:
            if elem.tag != "row":
                continue
            row = {col: elem.attrib.get(col, "") for col in columns}
            writer.writerow(row)
            row_count += 1
            elem.clear()

            if row_count % 500_000 == 0:
                elapsed = round(time.time() - t0, 1)
                log.info("    %d rows  %.1fs", row_count, elapsed)

    elapsed = round(time.time() - t0, 1)
    size_mb = csv_path.stat().st_size / (1024 * 1024)
    log.info("  %-20s  %10d rows  %7.1f MB  %.1fs",
             xml_path.stem, row_count, size_mb, elapsed)
    return row_count


def write_lookup(rows: list[tuple], csv_path: Path) -> None:
    """Write a static lookup table to CSV."""
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    log.info("  %-20s  %10d rows  (lookup)", csv_path.stem, len(rows) - 1)


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract Stack Exchange dump (.7z) and convert to CSV."
    )
    parser.add_argument(
        "--dump", default=None,
        help="Path to .7z dump file (e.g. stackoverflow.com.7z)"
    )
    parser.add_argument(
        "--xml_dir", default="xml",
        help="Directory with extracted XML files (default: xml/). "
             "Used directly if --dump is not provided."
    )
    parser.add_argument(
        "--csv_dir", default="csv",
        help="Output CSV directory (default: csv/)"
    )
    parser.add_argument(
        "--skip_large", action="store_true",
        help="Skip Posts and PostHistory (very large tables, hours to process)"
    )
    args = parser.parse_args()

    xml_dir = Path(args.xml_dir)
    csv_dir = Path(args.csv_dir)
    csv_dir.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("Stack Exchange Data Extractor")
    log.info("  XML dir    : %s", xml_dir)
    log.info("  CSV output : %s", csv_dir)
    log.info("=" * 60)

    # Step 1: Extract 7z if provided
    if args.dump:
        dump_path = Path(args.dump)
        if not dump_path.exists():
            raise FileNotFoundError(
                f"Dump file not found: {dump_path}\n"
                "Download from: stackoverflow.com → Settings → Data Dump"
            )
        extract_7z(dump_path, xml_dir)

    if not xml_dir.exists():
        raise FileNotFoundError(
            f"XML directory not found: {xml_dir}\n"
            "Either provide --dump <file.7z> or extract manually first."
        )

    # Step 2: Convert XML tables
    log.info("\nConverting XML tables to CSV ...")
    total_rows = 0
    failed     = []

    for table, columns in TABLES.items():
        if args.skip_large and table in ("Posts", "PostHistory"):
            log.info("  %-20s  SKIPPED (--skip_large)", table)
            continue

        xml_path = xml_dir / f"{table}.xml"
        csv_path = csv_dir / f"{table}.csv"

        if not xml_path.exists():
            log.warning("  %-20s  XML not found: %s", table, xml_path)
            failed.append(table)
            continue

        log.info("  %s ...", table)
        try:
            total_rows += xml_to_csv(xml_path, csv_path, columns)
        except Exception as e:
            log.error("  FAILED: %s — %s", table, e)
            failed.append(table)

    # Step 3: Write lookup tables
    log.info("\nWriting lookup tables ...")
    for table, rows in LOOKUP_TABLES.items():
        csv_path = csv_dir / f"{table}.csv"
        write_lookup(rows, csv_path)

    log.info("=" * 60)
    log.info("Done — %d XML tables, %d total rows", len(TABLES), total_rows)
    if failed:
        log.warning("Failed/missing: %s", failed)
    log.info("CSV files → %s/", csv_dir)
    log.info("Next step:")
    log.info("  python ../extract_schema.py --csv_dir csv "
             "--output schema.json --database StackOverflow")
    log.info("=" * 60)


if __name__ == "__main__":
    main()