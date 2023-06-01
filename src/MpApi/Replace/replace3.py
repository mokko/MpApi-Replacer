"""
After having experimented with the 1-field replacer (replace2.py), we try out replacing 
global documents next.

We want to use the same config toml format as for replace2.

We aim for a command line util that has similar interface as the replace2.
"""

import argparse
#import datetime
#from copy import deepcopy
from lxml import etree
from mpapi.client import MpApi
from mpapi.constants import NSMAP, parser
from mpapi.module import Module
from MpApi.Replace.baseApp import BaseApp, RIA_data
from pathlib import Path
#import sys

try:
    import tomllib  # Python v3.11
except ModuleNotFoundError:
    import tomli as tomllib  # < Python v3.11


class Replace3:
    def __init    def __init__(
        self,
        *,
        act: bool = False,
        baseURL: str,
        conf_fn: str,
        cache: bool = False,
        limit: int = -1,
        pw: str,
        user: str,
    ):
        super().__init__(act = act, baseURL=baseURL,conf_fn=conf_fn, cache=cache,pw=pw, user=user)

    def replace(self, *, search_results: Module) -> None:
        """
        Loops through all items in the search results and call the actions for the 
        current job (i.e. in the toml config file).
        """
        
        mtype = self.conf["module"]
        #avoid deep copy this time
        #so we loop thru one big document with many items

        IDs = search_results.xpath("/m:application/m:modules[@name='mtype']/m:moduleItem/@id")

        print (IDs)

        #for itemN in search_results.iter(module=mtype):

