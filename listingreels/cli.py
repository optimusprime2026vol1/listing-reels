"""listingreels command line interface."""
from __future__ import annotations

import argparse
import sys
import time

from .assemble import build_reel
from .config import load_config


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="listingreels")
    sub = parser.add_subparsers(dest="command", required=True)

    build_p = sub.add_parser("build", help="Build a reel from a listing config")
    build_p.add_argument("--listing", required=True, help="Path to a listing YAML config")
    build_p.add_argument("--quiet", action="store_true", help="Suppress progress output")
    build_p.add_argument("--out", help="Override the config's output path")

    args = parser.parse_args(argv)

    if args.command == "build":
        cfg = load_config(args.listing)
        if args.out:
            cfg.output = args.out
        verbose = not args.quiet
        if verbose:
            print(f"Building reel for: {cfg.title}  ({len(cfg.photos)} photos)")
        start = time.time()
        out = build_reel(cfg, verbose=verbose)
        if verbose:
            print(f"Done in {time.time() - start:.1f}s -> {out}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
