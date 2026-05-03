#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE_RE = re.compile(r'^\s*\.include\s+(?P<target>"[^"]+"|<[^>]+>|\S+)\s*(?:;.*)?$')

class IncludeError(RuntimeError):
    pass

def _decode_target(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
        return raw[1:-1]
    if len(raw) >= 2 and raw[0] == '<' and raw[-1] == '>':
        return raw[1:-1]
    return raw

def _candidate_paths(target: str, current_dir: Path, include_paths: list[Path]) -> list[Path]:
    target_path = Path(target)
    if target_path.is_absolute():
        return [target_path]
    candidates = [current_dir / target_path]
    candidates.extend(path / target_path for path in include_paths)
    return candidates

def _resolve_include(target: str, current_dir: Path, include_paths: list[Path]) -> Path:
    tried: list[Path] = []
    for candidate in _candidate_paths(target, current_dir, include_paths):
        candidate = candidate.resolve()
        tried.append(candidate)
        if candidate.is_file():
            return candidate
    tried_text = "\n".join(f"  - {p}" for p in tried)
    raise IncludeError(f"Cannot resolve include {target!r}. Tried:\n{tried_text}")

def expand_source(source: str, source_path: Path, include_paths: list[Path] | None = None, stack: list[Path] | None = None) -> str:
    include_paths = [p.resolve() for p in (include_paths or [])]
    source_path = source_path.resolve()
    current_dir = source_path.parent
    stack = stack or []
    if source_path in stack:
        chain = " -> ".join(str(p) for p in [*stack, source_path])
        raise IncludeError(f"Recursive include detected: {chain}")

    out: list[str] = []
    new_stack = [*stack, source_path]
    for line_no, line in enumerate(source.splitlines(), start=1):
        match = INCLUDE_RE.match(line)
        if not match:
            out.append(line)
            continue

        target = _decode_target(match.group('target'))
        include_path = _resolve_include(target, current_dir, include_paths)
        include_source = include_path.read_text(encoding='utf-8')
        out.append(f"; begin include: {include_path.as_posix()}")
        out.append(expand_source(include_source, include_path, include_paths, new_stack))
        out.append(f"; end include: {include_path.as_posix()}")

    if source.endswith('\n'):
        return "\n".join(out) + "\n"
    return "\n".join(out)

def expand_file(path: str | os.PathLike[str], include_paths: list[str | os.PathLike[str]] | None = None) -> str:
    source_path = Path(path).resolve()
    paths = [ROOT]
    if include_paths:
        paths.extend(Path(p) for p in include_paths)
    return expand_source(source_path.read_text(encoding='utf-8'), source_path, paths)

def main() -> None:
    parser = argparse.ArgumentParser(description='Flatten Sutra .include directives.')
    parser.add_argument('input', help='Input .sutra source')
    parser.add_argument('output', nargs='?', help='Output flattened .sutra source. If omitted, writes to stdout.')
    parser.add_argument('-I', '--include-path', action='append', default=[], help='Additional include search path')
    args = parser.parse_args()

    try:
        expanded = expand_file(args.input, args.include_path)
    except IncludeError as e:
        raise SystemExit(str(e)) from e

    if args.output:
        output_path = Path(args.output)
        if output_path.parent != Path(''):
            output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(expanded, encoding='utf-8', newline='\n')
        print(f"Expanded {args.input} -> {args.output}")
    else:
        sys.stdout.write(expanded)

if __name__ == '__main__':
    main()
