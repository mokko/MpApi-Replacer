"""
    Perhaps we need a new replacer. Replacer2 is dfferent from replacer1 in that it 
    - takes saved queries as input and 
    - sends update requests on a per field basis instead of global documents

    The command-line interface remains similar.

    It's very possible that RIA will let me only change certain field types and not on 
    others. For example, I assume I can't change any or most SystemFields. I hope we'll
    find out.
    
    new toml format describing a change job
        savedQuery = 538067   # p-TestAssets 
        module = "Multimedia" # Assets
        [[replace]]
        field = "systemField:__orgUnit"
        search = "EMMusikethnologie"
        replace = "EMMedienarchiv"
    
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
            act=act, baseURL=baseURL, conf_fn=conf_fn, cache=cache, pw=pw, user=user
        )

    def replace(self, *, search_results: Module) -> None:
        """
        Loops through all items in the search results calling the actions described
        for the current job (i.e. in the toml config file).

        There are only 6 field types in RIA. We'll test them in the order of complexity
            1. dataField
            2. systemField (__orgUnit)
            3. vocabularyReference/repeatableGroup
            4. composite
        We will not attempt to change virtualField.
        """

        mtype = self.conf["module"]

        for itemN in search_results.iter(module=mtype):
            # without copy the whole document is passed around
            # but I wanted only moduleItem fragments
            # next time I will extract an index of IDs and use that
            # to loop thru whole document.
            item2 = deepcopy(itemN)
            ID = self._id_from_item(item2)
            mtype = self.conf["module"]
            print(f"* {mtype} {ID}")
            self._replace_per_item(itemN=item2)

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

    # OBSOLETE
    def _mulTypeVoc(self, *, old: str, new: str, itemM: Module) -> None:
        """
        Rewrite itemN data according to action described in toml file.

        We assume we get only one item/record of the proper mtype passed here inside of
        itemM.

        itemM should be changed in place, so no return value necessary?

        <vocabularyReference name="MulTypeVoc" id="30341" instanceName="MulTypeVgr">
          <vocabularyReferenceItem id="31041" name="image">
            <formattedValue language="de">Digitale Aufnahme</formattedValue>
          </vocabularyReferenceItem>
         </vocabularyReference>
        we want to include the search value here to look only thru records/items with
        matching value -> not anymore. Let's be more generic
        """

        known_values = {
            "3 D": 1816105,
            "Dia": 1816113,
            "Digitale Aufnahme": 31041,
            "Scan": 1816145,
        }

        try:
            old_id = known_values[old]
        except:
            raise TypeError("Error: Unknown MulTypeVoc value '{old}'")

        try:
            new_id = known_values[new]
        except:
            raise TypeError("Error: Unknown MulTypeVoc value '{new}'")

        vocRefItemL = itemM.xpath(
            f"""/m:application/m:modules/m:module/m:moduleItem/m:vocabularyReference[
                @name = 'MulTypeVoc'
            ]/m:vocabularyReferenceItem[
                @id = {old_id}
            ]"""
        )

        if vocRefItemL:
            # only change data if this item actually has the search value
            attribs = vocRefItemL[0].attrib
            attribs["id"] = str(new_id)
            if "name" in attribs:
                del attribs["name"]
        else:
            print(f"MulTypeVoc: search value '{old}' not found")

    # OBSOLETE
    def _perItem(self, *, itemN, mtype: str) -> None:
        """
        OBSOLETE
        Process individual items (=record), expects itemN as a node

        This is the second step of the actual replacement process.

        As usual i have trouble with the ria (speciication), so I dont know which
        endpoint to use. For posterity, I want to change a simple value in a
        vocabularyReference.

        Options are:
        (a) update the whole record -> updateItem
        (b) update a single field, but unclear if zetcom treats vocRef as field
             -> updateFieldInGroup, seems very unlikely
        (c) update whole rGrp or rGrpItem -> updateRepeatableGroup

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

    def _replace_dataField(
        self, *, field: str, itemN, search: str, replace: str
    ) -> None:
        mtype = self.conf["module"]
        ID = self._id_from_item(itemN)
        # print (f"field {field}")
        # print(self._toString(itemN))
        field_content = itemN.xpath(
            f"/m:moduleItem/m:dataField[@name = '{field}']/m:value/text()",
            namespaces=NSMAP,
        )[0]
        if field_content == search:
            print(f"\tsearch found")
            if self.act:
                print("\tquering RIA for change")
                r = self.ria.updateField2(
                    mtype=mtype, ID=ID, dataField=field, value=replace
                )
                print("\t" + r)
            else:
                print("\tnot acting")
        else:
            print(f"\tsearch NOT found")

    def _replace_per_item(self, *, itemN) -> None:
        for action in self.conf["replace"]:
            field_type, field, voc = [x.strip() for x in action["field"].split(":")]
            search = action["search"]
            replace = action["replace"]
            print(f"** {field_type}: {field}\t{search} -> {replace}")
            if field_type == "dataField":
                self._replace_dataField(
                    field=field, itemN=itemN, search=search, replace=replace
                )
            elif field_type == "repeatableGroup":
                self._replace_repeatableGroup(
                    field=field, itemN=itemN, search=search, replace=replace, voc=voc
                )
            elif field_type == "systemField":
                self._replace_systemField(
                    field=field, itemN=itemN, search=search, replace=replace
                )
            elif field_type == "vocabularyReference":
                self._replace_vocabularyReference(
                    field=field, itemN=itemN, search=search, replace=replace
                )
            elif field_type == "composite":
                print("\tcomposite not implemented yet")
            elif field_type == "virtualField":
                raise SyntaxError(f"ERROR: No replacements for virtualFields!")
            else:
                raise SyntaxError(f"ERROR: Unknown field type: {field_type}")

    def _replace_repeatableGroup(
        self, *, field: str, itemN, search: str, replace: str, voc: str
    ) -> None:
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
        ID = self._id_from_item(itemN)
        search = int(search)
        replace = int(replace)
        rGrpN = itemN.xpath(
            f"/m:moduleItem/m:repeatableGroup[@name = '{field}']", namespaces=NSMAP
        )[0]

        refID = rGrpN.xpath("m:repeatableGroupItem/@id", namespaces=NSMAP)[0]

        # find the item with id from search
        rGrpItemL = rGrpN.xpath(
            f"""m:repeatableGroupItem[
                    m:vocabularyReference[
                        @name = '{voc}'
                    ]/m:vocabularyReferenceItem[
                        @id = '{search}'
                    ]
                ]""",
            namespaces=NSMAP,
        )
        print(f"rGrpItemN: {rGrpItemL[0]}")
        field_content = int(rGrpItemL[0].attrib["id"])
        # print ("voc {voc}")

        print(f"{mtype} {ID} {rGrpN} {voc}")
        # print (f"refID {refID}")

        if len(rGrpItemL) == 1:
            print("\tsearch found")
            print(f"refID {refID}")
            # print(self._toString(rGrpItemL[0]))
            vRefItemN = rGrpItemL[0].xpath(
                f"""
                m:vocabularyReference[
                        @name = '{voc}'
                    ]/m:vocabularyReferenceItem[
                        @id = '{search}'
                    ]""",
                namespaces=NSMAP,
            )[0]
            vRefItemN.attrib["id"] = str(replace)
            xml = f"""
                    <application xmlns="http://www.zetcom.com/ria/ws/module">
                        <modules>
                            <module name="{mtype}">
                                <moduleItem id="{ID}"/>
                            </module>
                        </modules>
                    </application>"""
            doc = etree.XML(xml)
            mItemN = doc.xpath(
                "/m:application/m:modules/m:module/m:moduleItem", namespaces=NSMAP
            )[0]
            mItemN.append(rGrpN)
            m = Module(tree=doc)
            m.uploadForm()
            xml = m.toString()
            print(m.toString())
            print("validating..")
            m.validate()
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
        elif len(rGrpItemL) > 1:
            raise TypeError("More than one hit is not yet implemented!")
        else:
            print(f"\tsearch NOT found")

    def _replace_systemField(
        self, *, field: str, itemN, search: str, replace: str
    ) -> None:
        raise SyntaxError("systemField doesn't work!")

        if field != "__orgUnit":
            raise SyntaxError("Only systemField:__orgUnit allowed!")
        mtype = self.conf["module"]
        ID = self._id_from_item(itemN)
        field_content = itemN.xpath(
            f"/m:moduleItem/m:systemField[@name = '{field}']/m:value/text()",
            namespaces=NSMAP,
        )[0]
        xml = f"""
            <application xmlns="http://www.zetcom.com/ria/ws/module">
                <modules>
                    <module name="{mtype}">
                        <moduleItem id="{ID}">
                            <systemField name="{field}">
                                 <value>{replace}</value>
                            </systemField>
                        </moduleItem>
                    </module>
                </modules>
            </application>                
        """

        if field_content == search:
            print(f"\tsearch found")
            if self.act:
                print("quering RIA for change")
                print(xml)
                r = self.ria.updateField(module=mtype, id=ID, dataField=field, xml=xml)
                print(f"\t{r}")
            else:
                print("\tnot acting")

    def _replace_vocabularyReference(
        self, *, field: str, itemN, search: str, replace: str
    ) -> None:
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

    def _smbapproval(self, *, old: str, new: str, itemM: Module) -> None:
        """
        Rewrite the smb approval. If old == "None", we test that there is no approval
        element and only add smb approal to the record if there was none before.

        <repeatableGroup name="MulApprovalGrp" size="1">
          <repeatableGroupItem id="10159204">
            <vocabularyReference name="TypeVoc" id="58635" instanceName="MulApprovalTypeVgr">
              <vocabularyReferenceItem id="1816002" name="SMB-digital">
                <formattedValue language="en">SMB-digital</formattedValue>
              </vocabularyReferenceItem>
            </vocabularyReference>
            <vocabularyReference name="ApprovalVoc" id="58634" instanceName="MulApprovalVgr">
              <vocabularyReferenceItem id="4160027" name="Ja">
                <formattedValue language="en">Ja</formattedValue>
              </vocabularyReferenceItem>
            </vocabularyReference>
          </repeatableGroupItem>
        </repeatableGroup>
        """

        if old == "None":
            resL = itemM.xpath(
                """/m:application/m:modules/m:module/m:moduleItem/m:repeatableGroup[
                @name = 'MulApprovalGrp'
            ]/m:repeatableGroupItem/m:vocabularyReference[
                @name = 'TypeVoc'
            ]/m:vocabularyReferenceItem[
                @id = '1816002'
            ]"""
            )

            if resL:
                # SMB approval exists already, but user requested that old value is None,
                # so we dont change anything in this record, i.e. return None now
                print(
                    "SMB approval is not None, but None requested, so not changing approval"
                )
                return
            else:
                print("Need to create a new MulApprovalGrp for SMB-Digital")
        elif old == "Ja":
            resL = itemM.xpath(
                """/m:application/m:modules/m:module/m:moduleItem/m:repeatableGroup[
                @name = 'MulApprovalGrp'
            ]/m:repeatableGroupItem/m:vocabularyReference[
                @name = 'TypeVoc'
            ]/m:vocabularyReferenceItem[
                @id = '1816002'
            ]"""
            )

        known_values = {
            "Ja": 4160027,
            "SMB-Digital": 1816002,
        }

        # rGrp=MulApprovalGrp could already exist
        # let's assume at first that MulApprovalGrp doesn't already exist
        if new == "Ja":
            today = datetime.date.today()
            xml = f"""
                <repeatableGroup xmlns="http://www.zetcom.com/ria/ws/module" name="MulApprovalGrp">
                  <repeatableGroupItem> 
                    <dataField dataType="Varchar" name="ModifiedByTxt">
                      <value>EM_SB</value>
                    </dataField>
                    <dataField dataType="Date" name="ModifiedDateDat">
                      <value>{today}</value>
                    </dataField>
                    <vocabularyReference name="TypeVoc" id="58635" instanceName="MulApprovalTypeVgr">
                      <vocabularyReferenceItem id="1816002"/>
                    </vocabularyReference>
                    <vocabularyReference name="ApprovalVoc" id="58634" instanceName="MulApprovalVgr">
                      <vocabularyReferenceItem id="4160027"/>
                    </vocabularyReference>
                  </repeatableGroupItem>
                </repeatableGroup>
            """

            itemN = itemM.xpath("/m:application/m:modules/m:module/m:moduleItem")[0]
            mulApprovalGrp = etree.fromstring(xml, parser)
            itemN.append(mulApprovalGrp)

    # should probably not be here
    def _toString(self, node) -> None:
        return etree.tostring(node, pretty_print=True, encoding="unicode")
