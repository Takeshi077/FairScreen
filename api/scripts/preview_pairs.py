from __future__ import annotations

import argparse
import random
import sys
from difflib import SequenceMatcher
from itertools import zip_longest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "api"))

from app.cvs.generator import generate_dataset  # noqa: E402
from app.cvs.names import ATTRIBUTE_ORDER  # noqa: E402


def side_by_side(left: str, right: str, width: int = 74) -> str:
    left_lines = left.splitlines()
    right_lines = right.splitlines()
    matcher = SequenceMatcher(None, left_lines, right_lines)
    rows: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in left_lines[i1:i2]:
                rows.append(f"  {line[:width]:<{width}} | {line[:width]}")
            continue
        for lline, rline in zip_longest(left_lines[i1:i2], right_lines[j1:j2], fillvalue=""):
            rows.append(f"- {lline[:width]:<{width}} | + {rline[:width]}")
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview matched CV pairs and their diffs")
    parser.add_argument("--pairs", type=int, default=3, help="number of pairs to print")
    parser.add_argument("--seed", type=int, default=2026, help="dataset seed")
    parser.add_argument(
        "--attribute",
        choices=[*ATTRIBUTE_ORDER, "all"],
        default="all",
        help="restrict preview to one attribute",
    )
    parser.add_argument(
        "--bases-per-role",
        type=int,
        default=33,
        help="base CVs per role used to build the preview pool",
    )
    args = parser.parse_args()

    specs = generate_dataset(seed=args.seed, bases_per_role=args.bases_per_role)
    candidates = []
    for spec in specs:
        attributes = ATTRIBUTE_ORDER if args.attribute == "all" else [args.attribute]
        for attribute in attributes:
            variants = spec.variants_for(attribute)
            if len(variants) >= 2:
                candidates.append((spec, attribute, variants))

    rng = random.Random(args.seed + 17)
    if not candidates:
        raise SystemExit("No pairs available for the requested attribute")
    chosen = rng.sample(candidates, k=min(args.pairs, len(candidates)))

    for number, (spec, attribute, variants) in enumerate(chosen, start=1):
        left, right = rng.sample(variants, k=2)
        print("=" * 150)
        print(f"Pair {number} | {spec.role} | tier: {spec.tier} | attribute: {attribute}")
        print(f"Left:  {left.group_name} ({left.label})")
        print(f"Right: {right.group_name} ({right.label})")
        print("Intended changed fields:", left.changed_fields)
        print("-" * 150)
        print(side_by_side(left.text, right.text))
        print()


if __name__ == "__main__":
    main()
