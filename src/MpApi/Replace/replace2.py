"""
    Replacer2 is the atomic replacer which make api requests per individual per field 
    changes. This method might be slower, but it leads to cleaner logs and is hence
    superior.

    Replacer2 is different from replacer1 in that it 
    - takes saved queries as input and
    - it allows only to replace existing values with new values
    In contrast to replacer3 it
    - sends update requests on a per field basis instead of item-wide changes
      which leads to cleaner log messages in RIA

    The command-line interface remains similar to replace1 and replace3.

    Usage:
        replacer2 -a -c

_per_item
    per command: new, add, sub, write, [new_or_write, add_or_new]
        
        per element:


Objektbeschreibung: Eine in Syrien gefertigte Oboe mit besonderen Intarsien.
Feld mit ID: X durch Y austauschen.


    
"""
import argparse
from copy import deepcopy
import datetime
from lxml import etree
from mpapi.client import MpApi
from mpapi.constants import NSMAP, parser
from mpapi.module import Module
from MpApi.Replace.baseApp import BaseApp
from MpApi.Fieldmaker import dataField, systemField, virtualField

from pathlib import Path
import sys

allowed_cmds = ("ADD", "ADD_OR_NEW", "NEW", "NEW_OR_WRITE", "SUB", "WRITE")


class ConfigError(Exception):
    pass


class FieldError(Exception):
    pass


class Replace2(BaseApp):
    def add(self, *, cmd: dict, data: Module, ID: int) -> None:
        """
        Add a string to an existing field, raise FieldError if field does not
        exist.

        Raises FieldError if applied to id-based field.
        """
        cmd["field"]

    def add_or_new(self, *, cmd: dict, data: Module, ID: int) -> None:
        """
        Like add, but creates a new field if it doesn't exist yet instead of raising an
        error.
        """
        pass

    def new(self, *, cmd: dict, data: Module, ID: int) -> None:
        """
        Create a new element with a certain value. Raises FieldError if field exists
        already.
        """
        if self._field_exists(cmd=cmd, data=data, ID=ID):
            raise FieldError("ERROR: New field exists already!")

        fieldL = cmd["field"].split(".")
        typeL = cmd["type"].split(".")
        mtype = self.conf["INPUT"]["mtype"]
        value = cmd["value"]

        for c in range(len(typeL)):
            if typeL[c] == "dataField":
                field = dataField(name=fieldL[c], value=value)
            if typeL[c] == "systemField":
                field = systemField(name=fieldL[c], value=value)
            if typeL[c] == "virtualField":
                field = virtualField(name=fieldL[c], value=value)

        # probably, we can make simple fields immediately
        # should we check the first type only or all of the fields?
        if (
            typeL[0] == "dataField"
            or typeL[0] == "systemField"
            or typeL[0] == "virtualField"
        ):
            print(f"Simple NEW: {typeL[0]} {fieldL[0]} {value}")
            self.ria.updateField2(mtype=mtype, ID=ID, dataField=fieldL[c], value=value)
        elif cmd["type"] == "repeatableGroup.dataField":
            # Das Problem hier ist, dass es zwar ObjPublicationGrp.NotesClb noch nicht gibt
            # aber ObjPublicationGrp schon. 
        
            xml = f"""
            <application xmlns="http://www.zetcom.com/ria/ws/module">
                <modules>
                    <module name="{mtype}">
                        <moduleItem id="{ID}">
                            <repeatableGroup name="{fieldL[0]}">
                                <repeatableGroupItem>
                                    <dataField name="{fieldL[1]}">
                                        <value>{value}</value>
                                    </dataField>
                                </repeatableGroupItem>
                            </repeatableGroup>
                        </moduleItem>
                    </module>
                </modules>
            </application>
            """
            # xml = xml.encode()
            print (xml)
            self.ria.createRepeatableGroup(
                module=mtype, repeatableGroup=fieldL[0], xml=xml, id=ID
            )
        else:
            print(f"not yet implemented: {cmd['type']}")

    def _field_exists(self, *, cmd: dict, data: Module, ID: int) -> bool:
        mtype = self.conf["INPUT"]["mtype"]
        fieldL = cmd["field"].split(".")
        typeL = cmd["type"].split(".")
        xpath = f"/m:application/m:modules/m:module[@name='{mtype}']/m:moduleItem[@id = '{ID}']"
        for c in range(len(typeL)):
            xpath += f"/m:{typeL[c]}[@name = '{fieldL[c]}']"
            if typeL[c] == "repeatableGroup":
                xpath += "/m:repeatableGroupItem"
            elif typeL[c] == "moduleReference":
                xpath += "/m:moduleReferenceItem"
            elif typeL[c] == "vocabularyReference":
                xpath += "/m:vocabularyReferenceItem"

        ret = data.xpath(xpath)
        print(f"DEBUG _field_exists {xpath} -> {ret}")
        # print (ret)
        if ret:
            return True
        else:
            return False

    def new_or_write(self, *, cmd: dict, data: Module, ID: int) -> None:
        """
        Like write, but creates a new element instead of raising an error.
        """
        pass

    def sub(self, *, cmd: dict, data: Module, ID: int) -> None:
        """
        Substract given value from the end of the given field. Raises FieldError if field
        doesn't exist or if it doesn't end on specified string.
        """
        pass

    def write(self, *, cmd: dict, data: Module, ID: int) -> None:
        """
        Overwrite current field value with new value. Raises FieldError if specified
        field does not exist.

        At the moment, we can't replace partial field values.
        """
        pass

    #
    # private
    #

    def _per_item(self, *, doc: Module, ID: int) -> None:
        """
        Gets called during replace for every moduleItem.
        """
        # mtype = self.conf["INPUT"]["mtype"]
        # print(self.conf)
        # print(f"  {mtype} {ID}")
        for cmd in self.conf:
            if cmd == "FILTER" or cmd == "INPUT":
                continue
            for specific in self.conf[cmd]:
                print(f"* {cmd} {specific}")
                if cmd == "ADD":
                    try:
                        self.add(cmd=specific, data=doc, ID=ID)
                    except FieldError:
                        print(f"{cmd}: error")
                elif cmd == "ADD_OR_NEW":
                    try:
                        self.add_or_new(cmd=specific, data=doc, ID=ID)
                    except FieldError:
                        print(f"{cmd}: raises")
                elif cmd == "NEW":
                    try:
                        self.new(cmd=specific, data=doc, ID=ID)
                    except FieldError:
                        print(
                            f"{cmd}: '{specific['field']}' exists already; do nothing"
                        )
                elif cmd == "NEW_OR_WRITE":
                    try:
                        self.new_or_write(cmd=specific, data=doc, ID=ID)
                    except FieldError:
                        print(f"{cmd}: raises")
                elif cmd == "SUB":
                    try:
                        self.sub(cmd=specific, data=doc, ID=ID)
                    except FieldError:
                        print(f"{cmd}: something clever")
                elif cmd == "WRITE":
                    try:
                        self.write(cmd=specific, data=doc, ID=ID)
                    except FieldError:
                        print(f"{cmd}: something clever")
                else:
                    raise ConfigError(f"Unknown Command: {cmd}")

    #
    # OLD STUFF
    #

    # should be in a data oriented class?
    def _id_from_item(self, itemN) -> int:
        """
        Returns id of the first moduleItem as int. Expects an xml fragment for
        moduleItem.
        """
        return int(itemN.xpath("/m:moduleItem/@id", namespaces=NSMAP)[0])

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
