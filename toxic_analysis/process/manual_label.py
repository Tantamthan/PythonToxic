r"""
Manual labeling helper for collected comments.

Usage from project root:
  .\.venv\Scripts\python.exe .\toxic_analysis\process\manual_label.py export --limit 100
  .\.venv\Scripts\python.exe .\toxic_analysis\process\manual_label.py import
  .\.venv\Scripts\python.exe .\toxic_analysis\process\manual_label.py status
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "collected"
DEFAULT_REVIEW = DATA_DIR / "manual_review.csv"
DEFAULT_LABELED = DATA_DIR / "labeled_collected.csv"
VALID_LABELS = {"CLEAN", "OFFENSIVE", "HATE"}
SOURCE_FILES = {
    "youtube": "youtube_comments.csv",
    "reddit": "reddit_comments.csv",
    "facebook": "facebook_comments.csv",
}


try:
    from label_data import _tao_khoa_ban_ghi
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from label_data import _tao_khoa_ban_ghi


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def ensure_record_key(
    df: pd.DataFrame,
    text_col: str = "text",
    default_source: str = "reddit",
) -> pd.DataFrame:
    df = df.copy()
    if "source" not in df.columns:
        df["source"] = default_source
    if "record_key" not in df.columns:
        df["record_key"] = _tao_khoa_ban_ghi(df, text_col)
    return df


def normalize_labels(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.upper()


def cmd_status(args: argparse.Namespace) -> None:
    source_df = read_csv(args.source)
    review_df = read_csv(args.review)
    labeled_df = read_csv(args.labeled)

    print(f"Source pending : {len(source_df):,} rows -> {args.source}")
    print(f"Manual review  : {len(review_df):,} rows -> {args.review}")
    print(f"Labeled cache  : {len(labeled_df):,} rows -> {args.labeled}")

    if "label" in review_df.columns and not review_df.empty:
        counts = normalize_labels(review_df["label"]).value_counts(dropna=False)
        print("\nmanual_review.csv labels:")
        for label, count in counts.items():
            shown = label if label else "<blank>"
            print(f"  {shown}: {count:,}")

    if "label" in labeled_df.columns and not labeled_df.empty:
        counts = normalize_labels(labeled_df["label"]).value_counts(dropna=False)
        print("\nlabeled_collected.csv labels:")
        for label, count in counts.items():
            shown = label if label else "<blank>"
            print(f"  {shown}: {count:,}")


def cmd_export(args: argparse.Namespace) -> None:
    if args.review.exists() and not args.overwrite:
        raise SystemExit(
            f"{args.review} already exists. Fill/import it first, or rerun with --overwrite."
        )

    source_df = read_csv(args.source)
    if source_df.empty:
        raise SystemExit(f"No pending rows found in {args.source}")
    if "text" not in source_df.columns:
        raise SystemExit(f"{args.source} must contain a 'text' column")

    source_df = ensure_record_key(source_df, default_source=args.platform)
    limit = min(args.limit, len(source_df)) if args.limit > 0 else len(source_df)
    review_df = source_df.head(limit).copy()

    # Put label near the front for easier editing in Excel.
    review_df["label"] = ""
    front = [
        col
        for col in [
            "record_key",
            "label",
            "text",
            "comment_id",
            "video_id",
            "subreddit",
            "facebook_group_id",
            "post_id",
            "post_url",
            "post_title",
            "author",
            "score",
            "published_at",
            "source",
        ]
        if col in review_df.columns
    ]
    rest = [col for col in review_df.columns if col not in front]
    review_df = review_df[front + rest]

    write_csv(review_df, args.review)
    print(f"Exported {len(review_df):,} rows for manual labeling -> {args.review}")
    print("Fill the 'label' column with CLEAN, OFFENSIVE, or HATE, then run import.")


def cmd_import(args: argparse.Namespace) -> None:
    review_df = read_csv(args.review)
    if review_df.empty:
        raise SystemExit(f"No review rows found in {args.review}")
    if "label" not in review_df.columns:
        raise SystemExit(f"{args.review} must contain a 'label' column")
    if "text" not in review_df.columns:
        raise SystemExit(f"{args.review} must contain a 'text' column")

    review_df = ensure_record_key(review_df, default_source=args.platform)
    review_df["label"] = normalize_labels(review_df["label"])

    valid_mask = review_df["label"].isin(VALID_LABELS)
    invalid_filled = review_df["label"].ne("") & ~valid_mask
    if invalid_filled.any():
        bad = review_df.loc[invalid_filled, ["record_key", "label", "text"]].head(10)
        print("Invalid labels found. Allowed labels: CLEAN, OFFENSIVE, HATE")
        print(bad.to_string(index=False))
        raise SystemExit(1)

    labeled_now = review_df[valid_mask].copy()
    remaining_review = review_df[~valid_mask].copy()
    if labeled_now.empty:
        raise SystemExit("No valid manual labels found. Fill the 'label' column first.")

    labeled_now["labeled_by"] = args.labeled_by
    if "source" not in labeled_now.columns:
        labeled_now["source"] = args.platform
    if "split" not in labeled_now.columns:
        labeled_now["split"] = "collected"

    labeled_df = read_csv(args.labeled)
    if not labeled_df.empty:
        labeled_df = ensure_record_key(labeled_df, default_source=args.platform)
    combined = pd.concat([labeled_df, labeled_now], ignore_index=True, sort=False)
    combined = ensure_record_key(combined, default_source=args.platform)
    combined = combined[combined["label"].isin(VALID_LABELS)].copy()
    combined = combined.drop_duplicates(subset=["record_key"], keep="last")
    write_csv(combined, args.labeled)

    source_df = read_csv(args.source)
    removed = 0
    if not source_df.empty:
        source_df = ensure_record_key(source_df, default_source=args.platform)
        done_keys = set(labeled_now["record_key"].astype(str))
        before = len(source_df)
        source_df = source_df[~source_df["record_key"].astype(str).isin(done_keys)].copy()
        removed = before - len(source_df)
        write_csv(source_df, args.source)

    if remaining_review.empty or args.clear_review:
        if args.review.exists():
            args.review.unlink()
    else:
        # Keep blank rows in manual_review.csv so the user can continue later.
        remaining_review["label"] = ""
        write_csv(remaining_review, args.review)

    print(f"Imported {len(labeled_now):,} manual labels -> {args.labeled}")
    print(f"Removed {removed:,} rows from pending source -> {args.source}")
    if remaining_review.empty or args.clear_review:
        print(f"Cleared review file -> {args.review}")
    else:
        print(f"Kept {len(remaining_review):,} unlabeled rows in -> {args.review}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export/import manual labels for collected social comments."
    )
    parser.add_argument("--platform", choices=SOURCE_FILES.keys(), default="reddit")
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--labeled", type=Path, default=DEFAULT_LABELED)

    subparsers = parser.add_subparsers(dest="command", required=True)

    export = subparsers.add_parser("export", help="Export pending rows to manual_review.csv")
    export.add_argument("--limit", type=int, default=100, help="Rows to export; 0 means all")
    export.add_argument("--overwrite", action="store_true", help="Replace existing review file")
    export.set_defaults(func=cmd_export)

    import_cmd = subparsers.add_parser("import", help="Import filled manual_review.csv")
    import_cmd.add_argument("--labeled-by", default="Manual")
    import_cmd.add_argument(
        "--clear-review",
        action="store_true",
        help="Delete manual_review.csv after importing valid labels, even if some rows are blank",
    )
    import_cmd.set_defaults(func=cmd_import)

    status = subparsers.add_parser("status", help="Show pending/review/labeled counts")
    status.set_defaults(func=cmd_status)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.source is None:
        args.source = DATA_DIR / SOURCE_FILES[args.platform]
    args.func(args)


if __name__ == "__main__":
    main()
