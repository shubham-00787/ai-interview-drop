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
    pub.add_argument("--no-send", action="store_true", help="publish to the site + PDF only; email later with send-latest")
    sub.add_parser("send-latest", help="email the newest issue if it hasn't been emailed yet")
    sub.add_parser("send-test", help="email the latest issue to SENDER_EMAIL only (via Gmail if configured)")
    sub.add_parser("site", help="re-render the website from past issues")
    a = p.parse_args()
    if a.cmd == "collect":
        pipeline.run_daily()
    elif a.cmd == "seed":
        pipeline.run_seed_refresh()
    elif a.cmd == "publish":
        from . import issue
        issue.publish(dry_run=a.dry_run, send_now=not a.no_send)
    elif a.cmd == "send-latest":
        from . import issue
        issue.send_latest()
    elif a.cmd == "send-test":
        from . import issue
        issue.send_test()
    elif a.cmd == "site":
        from . import render
        render.build_site()


if __name__ == "__main__":
    main()
