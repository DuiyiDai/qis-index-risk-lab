import argparse
import json
from pathlib import Path
from .data import load_csv, validate
from .engine import run
from .reporting import demo, build_site, persist


def main():
    parser = argparse.ArgumentParser(
        description="QIS Index & Risk Lab: offline educational research"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("demo")
    p.add_argument("--out", default="results/synthetic")
    p = sub.add_parser("validate")
    p.add_argument("folder")
    p = sub.add_parser("historical")
    p.add_argument("folder")
    p.add_argument("--out", default="private-results")
    p = sub.add_parser("build-site")
    p.add_argument("--results", default="results/synthetic")
    p.add_argument("--out", default="site")
    args = parser.parse_args()
    if args.command == "demo":
        b = demo(args.out)
        print(f"Synthetic demo complete: {b['as_of']}; {len(b['summary'])} scenarios")
    elif args.command == "validate":
        print(json.dumps(validate(load_csv(args.folder)), indent=2))
    elif args.command == "historical":
        d = load_csv(args.folder)
        if d.metadata["mode"] != "historical":
            raise ValueError("historical command rejects synthetic inputs")
        # Keep every historical run inside an explicitly private directory.
        if "private-results" not in Path(args.out).parts:
            raise ValueError("historical output must be within private-results/")
        rows, state = run(d)
        print(persist(d, rows, state, args.out))
    else:
        print(build_site(args.results, args.out))


if __name__ == "__main__":
    main()
