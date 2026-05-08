from pathlib import Path
import argparse
import sys


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write(path, text):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description="Compose a Gowin CST file from smaller CST fragments.")
    parser.add_argument("output", help="Output CST path")
    parser.add_argument("fragments", nargs="+", help="Input CST fragments in composition order")
    args = parser.parse_args()

    chunks = []
    for fragment in args.fragments:
        path = Path(fragment)
        if not path.is_file():
            print(f"Missing fragment: {path}", file=sys.stderr)
            return 2
        chunks.append(f"// BEGIN {path.as_posix()}\n")
        chunks.append(read(path).rstrip() + "\n")
        chunks.append(f"// END {path.as_posix()}\n\n")

    write(args.output, "".join(chunks).rstrip() + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
