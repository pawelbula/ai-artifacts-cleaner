from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aac.core import clean_file, find_images, scan_file


def _cmd_scan(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.paths]
    images = find_images(paths, recursive=args.recursive)
    if not images:
        print("No supported image files found.")
        return 1

    dirty_count = 0
    for path in images:
        report = scan_file(path)
        status = "CLEAN" if report.is_clean else "CONTAINS METADATA"
        print(f"\n{path}  [{status}]")
        print(f"  format: {report.format}, size: {report.size}, mode: {report.mode}")
        print(f"  EXIF: {report.exif_tag_count} fields")
        print(f"  ICC profile: {'yes' if report.has_icc else 'no'}")
        print(f"  XMP: {'yes' if report.has_xmp else 'no'}")
        print(f"  C2PA/JUMBF (AI marker): {'YES' if report.has_c2pa else 'no'}")
        if report.ai_hints:
            print(f"  AI hints found in file: {', '.join(sorted(set(report.ai_hints)))}")
        if report.is_animated:
            print("  Note: animated/multi-frame file")
        if not report.is_clean:
            dirty_count += 1

    print(f"\nSummary: {dirty_count}/{len(images)} file(s) contain metadata.")
    return 0


def _cmd_clean(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.paths]
    images = find_images(paths, recursive=args.recursive)
    if not images:
        print("No supported image files found.")
        return 1

    if args.in_place and args.output:
        print("Error: --in-place and --output cannot be used together.", file=sys.stderr)
        return 2

    ok_count = 0
    skipped_count = 0
    for path in images:
        if args.in_place:
            output_path = path
        elif args.output:
            out_dir = Path(args.output)
            if len(paths) == 1 and paths[0].is_dir():
                rel = path.relative_to(paths[0])
                output_path = out_dir / rel
            else:
                output_path = out_dir / path.name
        else:
            output_path = path.with_name(f"{path.stem}_clean{path.suffix}")

        if args.dry_run:
            report = scan_file(path)
            action = "skipped (already clean)" if report.is_clean else f"would clean -> {output_path}"
            print(f"[dry-run] {path}: {action}")
            continue

        result = clean_file(path, output_path, quality=args.quality, keep_icc=args.keep_color_profile)
        if result.skipped:
            print(f"SKIPPED {path}: {result.reason}")
            skipped_count += 1
            continue

        removed = []
        if result.before.exif_tag_count:
            removed.append(f"EXIF ({result.before.exif_tag_count} fields)")
        if result.before.has_icc and not args.keep_color_profile:
            removed.append("ICC")
        if result.before.has_xmp:
            removed.append("XMP")
        if result.before.has_c2pa:
            removed.append("C2PA/JUMBF")
        summary = ", ".join(removed) if removed else "nothing to remove"
        print(f"OK {path} -> {result.output}  [removed: {summary}]")
        ok_count += 1

    if not args.dry_run:
        print(f"\nDone: cleaned {ok_count} file(s), skipped {skipped_count}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aac",
        description="Removes metadata (EXIF/XMP/ICC) and AI traces (C2PA/JUMBF) from images.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan_p = sub.add_parser("scan", help="Show what metadata/AI artifacts a file contains")
    scan_p.add_argument("paths", nargs="+", help="Files or directories to check")
    scan_p.add_argument("-r", "--recursive", action="store_true", help="Recurse into directories")
    scan_p.set_defaults(func=_cmd_scan)

    clean_p = sub.add_parser("clean", help="Remove metadata and write a cleaned copy of the file")
    clean_p.add_argument("paths", nargs="+", help="Files or directories to clean")
    clean_p.add_argument("-r", "--recursive", action="store_true", help="Recurse into directories")
    clean_p.add_argument("-o", "--output", help="Output directory for cleaned files")
    clean_p.add_argument("--in-place", action="store_true", help="Overwrite the original files (no backup!)")
    clean_p.add_argument("--quality", type=int, default=95, help="JPEG save quality (default 95)")
    clean_p.add_argument(
        "--keep-color-profile",
        action="store_true",
        help="Keep the ICC color profile (removed by default)",
    )
    clean_p.add_argument("--dry-run", action="store_true", help="Show what would be done without writing files")
    clean_p.set_defaults(func=_cmd_clean)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
