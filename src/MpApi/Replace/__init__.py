"""An Unofficial Client for the MuseumPlus API"""

__version__ = "0.0.1"
import argparse

# from mpapi.client import MpApi
from mpapi.constants import credentials

# from mpapi.module import Module
from pathlib import Path
from MpApi.Replace.replace1 import Replace1
from MpApi.Replace.replace2 import Replace2

if Path(credentials).exists():
    with open(credentials) as f:
        exec(f.read())


def replace1():
    # credentials = "emem1.py"  # in pwd
    parser = argparse.ArgumentParser(description="Command line frontend for Replace.py")
    parser.add_argument(
        "-l",
        "--lazy",
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
        "-L", "--Limit", help="set limit for initial search", default="-1"
    )
    args = parser.parse_args()
    replacer = Replace1(baseURL=baseURL, pw=pw, user=user, lazy=args.lazy, act=args.act)
    plugin = replacer.job(plugin=args.job)
    replacer.runPlugin(plugin=plugin, limit=args.Limit)  # set to -1 for production


def replacer2():
    parser = argparse.ArgumentParser(
        description="Command line frontend for Replace2.py"
    )
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
        "-j", "--job", help="load a job config 'replace2.toml' and execute it"
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

    replacer = Replace2(
        act=args.act,
        baseURL=baseURL,
        job=args.job,
        cache=args.cache,
        pw=pw,
        user=user,
    )
    dataM = replacer.search()
    replacer.replace(search_result=dataM)
