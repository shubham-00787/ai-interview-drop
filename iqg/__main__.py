"""python -m iqg collect | seed | publish [--dry-run] | site"""
import argparse

from . import pipeline


def main():
    p = argparse.ArgumentParser(prog="iqg")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("collect", help="daily: gather fresh questions, tag, dedupe")
    sub.add_parser("seed", help="re-read the curated GitHub repos for new questions")
    pub = sub.add_parser("publish", help="build the next issue, update the site, email subscribers")
    pub.add_argument("--dry-run", action="store_true", help="build + render a preview, but don't send or record")
    sub.add_parser("site", help="re-render the website from past issues")
    a = p.parse_args()
    if a.cmd == "collect":
        pipeline.run_daily()
    elif a.cmd == "seed":
        pipeline.run_seed_refresh()
    elif a.cmd == "publish":
        from . import issue
        issue.publish(dry_run=a.dry_run)
    elif a.cmd == "site":
        from . import render
        render.build_site()


if __name__ == "__main__":
    main()
