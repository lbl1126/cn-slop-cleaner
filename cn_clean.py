"""Flag English phrases from stop-slop and Chinese AI stock phrases.

The English phrase list is vendored from stop-slop under third_party/.
This file adds a Windows command-line checker and the Chinese patterns
in cn_patterns.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PHRASES_MD = ROOT / "third_party" / "stop-slop" / "phrases.md"
CN_PATTERNS = ROOT / "cn_patterns.json"

STRUCTURAL = [
    (
        re.compile(r"不是[^。！？\n]{1,80}而是"),
        "把后半句直接写成事实，前半句的否定通常没有新信息",
    ),
    (
        re.compile(r"不仅仅是"),
        "写成那一件具体的事",
    ),
    (
        re.compile(r"\bnot just\b.{0,80}\bbut\b", re.IGNORECASE),
        "State the positive claim. Drop the contrast.",
    ),
    (
        re.compile(r"\bit(?:'s| is) not\b.{0,80}\bit(?:'s| is)\b", re.IGNORECASE),
        "State what it is. Drop the 'it's not' half.",
    ),
]


def load_stop_slop(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    found: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(kind: str, needle: str) -> None:
        needle = needle.strip()
        if len(needle) < 4:
            return
        key = needle.casefold()
        if key in seen:
            return
        seen.add(key)
        found.append((kind, needle))

    for raw in re.findall(r'"([^"\n]+)"', text):
        if "[X]" in raw or "[x]" in raw:
            prefix = raw.split("[", 1)[0].strip(" :")
            add("prefix", prefix)
        else:
            add("exact", raw.rstrip("."))

    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        left = cells[0]
        if left in {"Avoid", "---"} or set(left) <= {"-", " "}:
            continue
        if left.startswith("-"):
            continue
        add("exact", left)

    return found


def load_chinese(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("cn_patterns.json must be a list")
    return data


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def scan(text: str, english: list[tuple[str, str]], chinese: list[dict[str, str]]) -> list[str]:
    hits: list[str] = []
    lowered = text.casefold()

    for kind, needle in english:
        if kind == "prefix":
            pattern = re.compile(re.escape(needle.casefold()))
            for match in pattern.finditer(lowered):
                hits.append(
                    f"[en] L{line_of(text, match.start())}: {needle} — cut this opener"
                )
        else:
            pattern = re.compile(re.escape(needle.casefold()))
            for match in pattern.finditer(lowered):
                hits.append(
                    f"[en] L{line_of(text, match.start())}: {needle} — remove or replace with a plain verb"
                )

    for rule in chinese:
        needle = rule["match"]
        hint = rule["hint"]
        start = 0
        while True:
            index = text.find(needle, start)
            if index < 0:
                break
            hits.append(f"[zh] L{line_of(text, index)}: {needle} — {hint}")
            start = index + len(needle)

    for pattern, hint in STRUCTURAL:
        for match in pattern.finditer(text):
            snippet = match.group(0).replace("\n", " ")
            hits.append(f"[structure] L{line_of(text, match.start())}: {snippet} — {hint}")

    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flag stock AI phrases in Chinese and English prose.")
    parser.add_argument("file", nargs="?", help="Text file. Reads stdin when omitted.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in checks and exit.")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    if not PHRASES_MD.is_file():
        print(f"missing upstream list: {PHRASES_MD}", file=sys.stderr)
        return 2

    english = load_stop_slop(PHRASES_MD)
    chinese = load_chinese(CN_PATTERNS)
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    hits = scan(text, english, chinese)
    print(f"hits: {len(hits)}")
    for line in hits:
        print(line)
    return 0


def run_self_test() -> int:
    english = load_stop_slop(PHRASES_MD)
    chinese = load_chinese(CN_PATTERNS)
    sample = "\n".join(
        [
            "It's worth noting that the export finished.",
            "Let that sink in.",
            "值得注意的是，导出已经完成。",
            "这不是功能列表，而是一次交付。",
        ]
    )
    hits = scan(sample, english, chinese)
    joined = "\n".join(hits)
    expected = [
        "It's worth noting",
        "Let that sink in",
        "值得注意的是",
        "不是功能列表，而是",
    ]
    missing = [item for item in expected if item not in joined]
    if missing:
        print("self-test failed, missing:", ", ".join(missing), file=sys.stderr)
        print(joined, file=sys.stderr)
        return 1
    if len(english) < 20:
        print(f"self-test failed, only parsed {len(english)} English phrases", file=sys.stderr)
        return 1
    print(f"self-test ok, english_phrases={len(english)}, chinese_patterns={len(chinese)}, sample_hits={len(hits)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
