"""Normalize generated API HTML punctuation after dox, preserving other bytes."""
import argparse
from pathlib import Path


DISALLOWED = chr(0x2014).encode("utf-8")


def normalize_api_docs(folder: Path):
    """Return (changed HTML files, replaced occurrences); never touch other files."""
    if not folder.is_dir():
        raise ValueError(f"Generated API documentation folder does not exist: {folder}")
    changed = occurrences = 0
    for path in folder.rglob("*"):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() != ".html":
            continue
        original = path.read_bytes()
        count = original.count(DISALLOWED)
        if count:
            path.write_bytes(original.replace(DISALLOWED, b"-"))
            changed += 1
            occurrences += count
    return changed, occurrences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", type=Path, default=Path("docs"))
    args = parser.parse_args()
    changed, occurrences = normalize_api_docs(args.docs)
    print(f"Normalized {occurrences} punctuation occurrences in {changed} generated API HTML files.")


if __name__ == "__main__":
    main()
