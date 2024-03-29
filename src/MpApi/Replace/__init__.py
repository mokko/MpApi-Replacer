"""MpApi.Replace - Several replacer tools for MpApi"""

__version__ = "0.0.4"  # new: replace3.py
import argparse

from mpapi.constants import get_credentials
from pathlib import Path

from MpApi.Replace.replace1 import Replace1
from MpApi.Replace.replace2 import Replace2  # atomic replacer
from MpApi.Replace.replace3 import Replace3  # discontinued atm

user, pw, baseURL = get_credentials()


def replacer1():
    parser = argparse.ArgumentParser(description="Command line frontend for Replace.py")
    parser.add_argument(
        "-c",
        "--cache",
        help="lazy modes reads search results from a file cache, for debugging",
        action="store_true",
    )
    parser.add_argument(
        "-a",
        "--act",
        help="include action, without it only show what would be changed",
        action="store_true",
    )
    parser.add_argument(
        "-j", "--job", help="load a plugin and use that code", required=True
    )
    parser.add_argument(
        "-l", "--limit", help="set limit for initial search", default="-1"
    )
    parser.add_argument(
        "-v",
        "--version",
        help="show program's version",
        action="store_true",
    )
    args = parser.parse_args()
    if args.version:
        print(__version__)
        raise SystemExit
    r = Replace1(baseURL=baseURL, pw=pw, user=user, lazy=args.cache, act=args.act)
    plugin = r.job(plugin=args.job)
    r.runPlugin(plugin=plugin, limit=args.limit)


def _replace(parser) -> dict:
    parser.add_argument(
        "-c",
        "--cache",
        help="reads search results from a file cache (aka lazy mode)",
        action="store_true",
    )
    parser.add_argument(
        "-a",
        "--act",
        help="actually make changes to RIA, without -a replacer2 only shows what would be changed",
        action="store_true",
    )
    parser.add_argument(
        "-j",
        "--job",
        help="load a config job and execute it",
    )
    parser.add_argument(
        "-l", "--limit", help="set limit for initial search", default="-1"
    )
    parser.add_argument(
        "-v",
        "--version",
        help="show program's version",
        action="store_true",
    )
    args = parser.parse_args()

    if args.version:
        print(__version__)
        raise SystemExit
    elif not args.job:
        raise SystemExit("--job|-j required")

    return args


def replacer2():
    parser = argparse.ArgumentParser(
        description="Command line frontend for Replace2.py"
    )
    args = _replace(parser)

    r = Replace2(
        act=args.act,
        baseURL=baseURL,
        conf_fn=args.job,
        cache=args.cache,
        pw=pw,
        user=user,
    )
    print("Searching...")
    dataM = r.search()
    print("Replacing...")
    # r.replace(search_results=dataM)


def replacer3():
    parser = argparse.ArgumentParser(
        description="Command line frontend for Replace3.py"
    )
    args = _replace(parser)

    r = Replace3(
        act=args.act,
        baseURL=baseURL,
        conf_fn=args.job,
        cache=args.cache,
        pw=pw,
        user=user,
    )
    print("Searching...")
    dataM = r.search()  # needs full records this time
    print("Replacing...")
    r.replace(search_results=dataM)
