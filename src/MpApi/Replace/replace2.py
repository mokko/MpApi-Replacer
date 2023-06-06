"""
    Replacer2 is different from replacer1 in that it 
    - takes saved queries as input and
    - it allows only to replace existing values with new values
    In contrast to replacer3 it
    - sends update requests on a per field basis instead of item-wide changes
      which leads to cleaner log messages in RIA

    The command-line interface remains similar to replace1 and replace3.

    Usage:
        replacer2 -a -c
    
"""


import argparse
import datetime
from copy import deepcopy
from lxml import etree
from mpapi.client import MpApi
from mpapi.constants import NSMAP, parser
from mpapi.module import Module
from pathlib import Path
from MpApi.Replace.baseApp import BaseApp
import sys


class ConfigError(Exception):
    pass


class Replace2(BaseApp):

    #
    # private
    #

    # should be in a data oriented class?
    def _id_from_item(self, itemN) -> int:
        """
        Returns id of the first moduleItem as int. Expects an xml fragment for
        moduleItem.
        """
        return int(itemN.xpath("/m:moduleItem/@id", namespaces=NSMAP)[0])

    def _perItem(self, *, itemN, mtype: str) -> None:
        """
        OBSOLETE
        Process individual items (=record), expects itemN as a node

        This is the second step of the actual replacement process.
        """
        Id = itemN.xpath("@id")[0]  # there can be only one
        xml = f"""
            <application xmlns="http://www.zetcom.com/ria/ws/module">
                <modules>
                    <module name="{mtype}"/>
                </modules>
            </application>"""
        outer = etree.fromstring(xml, parser)
        moduleN = outer.xpath("/m:application/m:modules/m:module", namespaces=NSMAP)[0]
        moduleN.append(itemN)
        itemM = Module(tree=outer)
        itemM.uploadForm()
        print(f"{mtype} {mulId}")
        for action in self.conf["actions"]:
            old = self.conf["actions"][action]["old"]
            new = self.conf["actions"][action]["new"]
            if mtype == "Multimedia":
                if action == "Typ":
                    self.MulTypeVoc(
                        itemM=itemM, old=old, new=new
                    )  # change data in place
                elif action == "SMB-Freigabe":
                    self.smbapproval(itemM=itemM, old=old, new=new)
                else:
                    raise TypeError(f"Not yet implemented: {action}")
            else:
                raise TypeError(f"Not yet implemented: {action}")

        fn = f"{mtype}-{mulId}.afterReplace.xml"
        print(f"Writing to {fn}")
        itemM.toFile(path=fn)
        itemM.validate()

        if self.act:
            # currently updates even if nothing has changed
            request = self.ria.updateItem2(mtype=mtype, ID=mulId, data=itemM)
            print(f"Status code: {request.status_code}")

    def _dataField(self, *, action: dict, data: Module, ID: int) -> None:
        mtype = self.conf["module"]
        # print (f"field {field}")
        # print(self._toString(itemN))

        valueN = data.xpath(
            f"""/m:application/m:modules/m:module[
                @name='{mtype}'
            ]/m:moduleItem[
                @id = '{ID}'
            ]/m:dataField[
                @name = '{field}'
            ]/m:value"""
        )[0]

        if valueN.text == action["s_in"]:
            print(f"\found; replacing ...")
            # valueN.text = action["r_in"]
            if self.act:
                print("\tquering RIA for change")
                r = self.ria.updateField2(
                    mtype=mtype, ID=ID, dataField=field, value=action["r_in"]
                )
                print("\t" + r)
            else:
                print("\tnot acting")
        else:
            print(f"\tsearch NOT found")

    def _per_item(self, *, doc: Module, ID: int) -> None:
        mtype = self.conf["module"]
        print(f"  {mtype} {ID}")
        for action in self.conf["replace"]:
            # print (f"action {action}")
            if action["field"][0] == "systemField":
                self._systemField(action=action, data=doc, ID=ID)
            elif action["field"][0] == "dataField":
                self._dataField(action=action, data=doc, ID=ID)
            elif action["field"][0] == "repeatableGroup":
                self._repeatableGroup(action=action, data=doc, ID=ID)
            elif action["field"][0] == "vocabularyReference":
                self._vocabularyReference(action=action, data=doc, ID=ID)
            else:
                raise SyntaxError("ERROR: Unknown field type!")

    def _repeatableGroup(self, *, action: dict, data: Module, ID: int) -> None:
        """
        replace one value in a repeatableGroup

        <repeatableGroup name="MulApprovalGrp" size="1">
          <repeatableGroupItem id="21046568" uuid="e354d8b8-199a-443e-ac0d-f3e570035cd9">
            <dataField dataType="Long" name="SortLnu">
              <value>1</value>
              <formattedValue language="de">1</formattedValue>
            </dataField>
            <dataField dataType="Varchar" name="ModifiedByTxt">
              <value>EM_MM</value>
            </dataField>
            <dataField dataType="Date" name="ModifiedDateDat">
              <value>2023-01-29</value>
              <formattedValue language="de">29.01.2023</formattedValue>
            </dataField>
            <vocabularyReference name="TypeVoc" id="58635" instanceName="MulApprovalTypeVgr">
              <vocabularyReferenceItem id="1816002" name="SMB-digital">
                <formattedValue language="de">SMB-digital</formattedValue>
              </vocabularyReferenceItem>
            </vocabularyReference>
            <vocabularyReference name="ApprovalVoc" id="58634" instanceName="MulApprovalVgr">
              <vocabularyReferenceItem id="4160027" name="Ja">
                <formattedValue language="de">Ja</formattedValue>
              </vocabularyReferenceItem>
            </vocabularyReference>
          </repeatableGroupItem>
        </repeatableGroup>
        """
        mtype = self.conf["module"]
        field = action["field"][1]
        subfield = action["field"][2]

        fieldN = data.xpath(
            f"""/m:application/m:modules/m:module[
                @name='{mtype}'
            ]/m:moduleItem[
                @id = '{ID}'
            ]/m:repeatableGroup[
                @name = '{field}' 
            ]"""
        )

        vRefItemN = fieldN.xpath(
            f"""m:repeatableGroupItem/m:vocabularyReference[
                @name = '{subfield}'
            ]/m:vocabularyReferenceItem""",
            namespaces=NSMAP,
        )[0]

        refID = vrefItemN.attribs["id"]
        print(f"    {action['s_in']} -> {action['r_in']} : {vRefItemN.attrib['id']}")
        if vRefItemN.attrib["id"] == action["s_in"]:
            print("\tfound; replacing...")
            vRefItemN.attrib["id"] = action["r_in"]
            del vRefItemN.attrib["name"]
            fvN = vRefItemN.xpath("m:formattedValue", namespaces=NSMAP)[0]
            vRefItemN.remove(fvN)
            xml = self._field2xml(fieldN)
        else:
            print(f"\tNOT found")
        print(f"{mtype} {ID} {field} {subfield} {refID}")

        if self.act:
            print("\tquering RIA for change")
            r = self.ria.updateRepeatableGroup(
                module=mtype,
                id=ID,
                referenceId=refID,
                repeatableGroup=field,
                xml=xml,
            )
            print(f"\t{r}")
        else:
            print("\tnot acting")

    def _systemField(self, *, action: dict, data: Module, ID: int) -> None:

        field = action["field"][1]
        if field != "__orgUnit":
            raise SyntaxError("Only systemField:__orgUnit allowed!")
        mtype = self.conf["module"]
        field_content = data.xpath(
            f"""/m:application/m:modules/m:module/m:moduleItem/m:systemField[
                @name = '{field}'
            ]/m:value/text()"""
        )[0]
        xml = f"""
            <application xmlns="http://www.zetcom.com/ria/ws/module">
                <modules>
                    <module name="{mtype}">
                        <moduleItem id="{ID}">
                            <systemField name="{field}">
                                 <value>{action['r_in']}</value>
                            </systemField>
                        </moduleItem>
                    </module>
                </modules>
            </application>"""

        if field_content == action["s_in"]:
            print(f"\tsearch found")
            if self.act:
                print("quering RIA for change")
                print(xml)
                xml = xml.encode()  # UTF8 as bytes?
                r = self.ria.updateField(module=mtype, id=ID, dataField=field, xml=xml)
                print(f"\t{r}")
            else:
                print("\tnot acting")

    def _vocabularyReference(self, *, action: dict, data: Module, ID: int) -> None:
        """
        Multimedia has many vocabularyReferences that allow a single term and only a few
        that allow multiple vocabularyReferenceItem.

        <vocabularyReference name="MulCategoryVoc" id="30330"
            instanceName="MulCategoryVgr">
          <vocabularyReferenceItem id="1055742" name="Audio">
            <formattedValue language="de">Audio</formattedValue>
          </vocabularyReferenceItem>
        </vocabularyReference>

        Upload format might be (guessed)
        <vocabularyReference name="MulCategoryVoc" id="30330">
          <vocabularyReferenceItem id="1055742"/> <!-- name="Audio"-->
        </vocabularyReference>
        """
        mtype = self.conf["module"]
        ID = self._id_from_item(itemN)
        search = int(search)
        replace = int(replace)
        refID = itemN.xpath(
            f"/m:moduleItem/m:vocabularyReference[@name = '{field}']/@id",
            namespaces=NSMAP,
        )[0]
        # here we simply take the first, instead we have to take the one with the search
        vRefN = itemN.xpath(
            f"/m:moduleItem/m:vocabularyReference[@name = '{field}']", namespaces=NSMAP
        )[0]
        vRefItemL = vRefN.xpath(
            f"m:vocabularyReferenceItem[@id = '{search}']", namespaces=NSMAP
        )
        field_content = int(vRefItemL[0].xpath("@id", namespaces=NSMAP)[0])

        if len(vRefItemL) == 1:
            print("\tsearch found")
            vRefItemL[0].attrib["id"] = str(replace)
            vRefItemL[0].attrib.pop("name")
            fvN = vRefItemL[0].xpath("m:formattedValue", namespaces=NSMAP)[0]
            vRefItemL[0].remove(fvN)
            # vRefN.attrib.pop("instanceName")
            xml = f"""
                    <application xmlns="http://www.zetcom.com/ria/ws/module">
                        <modules>
                            <module name="{mtype}">
                                <moduleItem id="{ID}"/>
                            </module>
                        </modules>
                    </application>"""
            m = Module(xml=xml)
            print("validating..")
            m.validate()
            shellN = etree.XML(xml)
            mItemN = shellN.xpath(
                "/m:application/m:modules/m:module/m:moduleItem", namespaces=NSMAP
            )[0]
            mItemN.append(vRefN)
            print(self._toString(shellN))
            if self.act:
                r = self.ria.updateRepeatableGroup(
                    module=mtype,
                    id=ID,
                    referenceId=refID,
                    repeatableGroup=field,
                    xml=xml,
                )
                print(f"\t{r}")
            else:
                print("\tnot acting")
        elif len(vRefItemL) > 1:
            raise TypeError("More than one hit is not yet implemented!")
        else:
            print(f"\tsearch NOT found")
