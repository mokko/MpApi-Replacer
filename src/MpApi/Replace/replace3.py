"""
After having experimented with the 1-field replacer (replace2.py), we try out replacing 
global documents next.

We want to use the same config toml format as for replace2.

We aim for a command line util that has similar interface as the replace2.
"""

import argparse

# import datetime
# from copy import deepcopy
from lxml import etree
from mpapi.client import MpApi
from mpapi.constants import NSMAP, parser
from mpapi.module import Module
from MpApi.Replace.baseApp import BaseApp, RIA_data
from pathlib import Path

# import sys

try:
    import tomllib  # Python v3.11
except ModuleNotFoundError:
    import tomli as tomllib  # < Python v3.11

import pprint


class Replace3(BaseApp):
    def __init__(
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
        super().__init__(
            act=act,
            baseURL=baseURL,
            conf_fn=conf_fn,
            cache=cache,
            limit=limit,
            pw=pw,
            user=user,
        )
        # pprint.pprint(self.conf)
        self.conf = self._rewrite_conf(self.conf)
        pprint.pprint(self.conf)

    def replace(self, *, search_results: Module) -> None:
        """
        Loops through all items in the search results and call the actions for the
        current job (i.e. in the toml config file).
        """

        mtype = self.conf["module"]
        IDs = search_results.xpath(
            f"/m:application/m:modules/m:module[@name='{mtype}']/m:moduleItem/@id"
        )

        # to avoid deep copy, so we loop thru one big document with many items
        for ID in IDs:
            self._per_item(doc=search_results, ID=ID)

    #
    # private
    #

    def _dataField(self, *, data, ID, action) -> bool:
        print("dataField not implemented yet")
        return False

    def _per_item(self, *, doc: Module, ID: int) -> None:
        mtype = self.conf["module"]
        print(f"  {mtype} {ID}")
        change = list()
        for action in self.conf["replace"]:
            # print (f"action {action}")
            if action["field"][0] == "systemField":
                c = self._systemField(action=action, data=doc, ID=ID)
                change.append(c)
            elif action["field"][0] == "dataField":
                c = self._dataField(action=action, data=doc, ID=ID)
                change.append(c)
            elif action["field"][0] == "repeatableGroup":
                c = self._repeatableGroup(action=action, data=doc, ID=ID)
                change.append(c)
            elif action["field"][0] == "vocabularyReference":
                c = self._vocabularyReference(action=action, data=doc, ID=ID)
                change.append(c)
            else:
                raise SyntaxError("ERROR: Unknown field type!")

        print(f"    change? {change}")
        if any(change):
            print("\tItem changed, attempting update ...")
            xml = self._completeItem(data=doc, ID=ID)
            m = Module(xml=xml)
            m.toFile(path=f"{mtype}{ID}.xml")
            # m.uploadForm()
            # xml = m.toString()
            # print (xml)
            xml = xml.encode()  # why is this necessary?
            r = self.ria.updateItem(module=mtype, id=ID, xml=xml)
            print(f"  {r}")

    def _repeatableGroup(self, *, data, ID, action):
        print("repeatableGroup not implemented yet")

    def _systemField(self, *, data: Module, ID, action):
        mtype = self.conf["module"]
        field = action["field"][1]
        valueN = data.xpath(
            f"""/m:application/m:modules/m:module[
                @name='{mtype}'
            ]/m:moduleItem[
                @id = '{ID}'
            ]/m:systemField[
                @name = '{field}'
            ]/m:value"""
        )[0]
        print(f"    {field} {action['s_in']} --> {action['r_in']}")
        print(f"    current value: {valueN.text}")
        if valueN.text == action["s_in"]:
            print(f"\tsearch value found, replacing field content")
            valueN.text = action["r_in"]
            return True
        else:
            print(f"    search value NOT found")
            return False

    def _vocabularyReference(self, *, data, ID, action):
        """
        TODO: Currently, I have only examples with a single vocRefItem, but I assume
        there could be multiple.
        """
        mtype = self.conf["module"]
        field = action["field"][1]
        vRefItemN = data.xpath(
            f"""/m:application/m:modules/m:module[
                @name='{mtype}'
            ]/m:moduleItem[
                @id = '{ID}'
            ]/m:vocabularyReference[
                @name = '{field}'
            ]/m:vocabularyReferenceItem"""
        )[0]
        itemId = int(vRefItemN.attrib["id"])
        del vRefItemN.attrib["name"]
        fvN = vRefItemN.xpath("m:formattedValue", namespaces=NSMAP)[0]
        vRefItemN.remove(fvN)
        print(f"    {field} {action['s_in']} --> {action['r_in']}")
        print(f"    current value: {itemId}")
        if itemId == action["s_in"]:
            print(f"\tsearch value found, replacing field content")
            vRefItemN.attrib["id"] = str(action["r_in"])
            return True
        else:
            print(f"    search value NOT found")
            return False
