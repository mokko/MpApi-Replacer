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


class Replace3(BaseApp):

    #
    # private
    #

    def _dataField(self, *, data, ID, action) -> bool:
        print(f"  * dataField {action['field'][1]}")
        mtype = self.conf["module"]
        field = action["field"][1]
        valueN = data.xpath(
            f"""/m:application/m:modules/m:module[
                @name='{mtype}'
            ]/m:moduleItem[
                @id = '{ID}'
            ]/m:dataField[
                @name = '{field}'
            ]/m:value"""
        )[0]
        print(f"    {action['s_in']} -> {action['r_in']}: {valueN.text}")
        if valueN.text == action["s_in"]:
            print(f"\found; replacing ...")
            valueN.text = action["r_in"]
            return True
        else:
            print(f"\tNOT found")
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

        print(f"Change? {change}")
        if any(change):
            self._updateItem(data=doc, ID=ID)

    def _repeatableGroup(self, *, data, ID, action):
        print(f"  * rGrp {action['field'][1]} {action['field'][2]}")
        mtype = self.conf["module"]
        field = action["field"][1]
        subfield = action["field"][2]

        vRefItemN = data.xpath(
            f"""/m:application/m:modules/m:module[
                @name='{mtype}'
            ]/m:moduleItem[
                @id = '{ID}'
            ]/m:repeatableGroup[
                @name = '{field}' 
            ]/m:repeatableGroupItem/m:vocabularyReference[
                @name = '{subfield}'
            ]/m:vocabularyReferenceItem"""
        )[0]
        print(f"    {action['s_in']} -> {action['r_in']} : {vRefItemN.attrib['id']}")
        if vRefItemN.attrib["id"] == action["s_in"]:
            print("\tfound; replacing...")
            vRefItemN.attrib["id"] = action["r_in"]
            del vRefItemN.attrib["name"]
            fvN = vRefItemN.xpath("m:formattedValue", namespaces=NSMAP)[0]
            vRefItemN.remove(fvN)
            return True
        else:
            print(f"\tNOT found")
            return False

    def _systemField(self, *, data: Module, ID, action):
        print(f"  * sysField {action['field'][1]}")
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
        print(f"    {action['s_in']} -> {action['r_in']}: {valueN.text}")
        if valueN.text == action["s_in"]:
            print("\tfound; replacing...")
            valueN.text = action["r_in"]
            return True
        else:
            print(f"\tvalue NOT found")
            return False

    def _updateItem(self, *, data: Module, ID: int):
        if self.act:
            print("\tItem changed, attempting update ...")
            mtype = self.conf["module"]
            xml = self._completeItem(data=data, ID=ID)
            m = Module(xml=xml)
            m.toFile(path=f"{mtype}{ID}.xml")
            # m.uploadForm()
            # xml = m.toString()
            # print (xml)
            xml = xml.encode()  # UTF8 as bytes?
            r = self.ria.updateItem(module=mtype, id=ID, xml=xml)
            print(f"  {r}")
        else:
            print("  no action mode")

    def _vocabularyReference(self, *, data, ID, action):
        """
        TODO: Currently, I have only examples with a single vocRefItem, but I assume
        there could be multiple.
        """
        print(f"  * vocRef {action['field'][1]}")
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
        print(f"    {action['s_in']} -> {action['r_in']}: {itemId}")
        if itemId == action["s_in"]:
            print("\tfound; replacing...")
            vRefItemN.attrib["id"] = str(action["r_in"])
            del vRefItemN.attrib["name"]
            fvN = vRefItemN.xpath("m:formattedValue", namespaces=NSMAP)[0]
            vRefItemN.remove(fvN)
            return True
        else:
            print(f"\tvalue NOT found")
            return False
