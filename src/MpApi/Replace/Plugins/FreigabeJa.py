import datetime
from mpapi.search import Search
from lxml import etree  # type: ignore
from mpapi.module import Module
from mpapi.constants import NSMAP

neinId = 4491690
jaId = 1810139

"""
    WARNING: This is quick and dirty. 

    TASK: For the records in one or more groups, set them to SMB-Freigabe = Ja if 
    Freigabe is not already "Ja".

    There are three possible cases for the situation
    (a) no SMBfreigabe has NOT been set before -> add/create a new one
    (b) SMBfreigabe = Ja -> do nothing
    (c) SMBfreigabe = Nein -> change to Ja
    (d) SMBfreigabe = None -> change to Ja

    <repeatableGroup name="ObjPublicationGrp" size="1">
      <repeatableGroupItem id="54108205" uuid="8e798bbb-6840-49ef-aea4-87260f37277b">
        <dataField dataType="Date" name="ModifiedDateDat">
          <value>2023-06-06</value>
          <formattedValue language="de">06.06.2023</formattedValue>
        </dataField>
        <dataField dataType="Varchar" name="ModifiedByTxt">
          <value>EM_MM</value>
        </dataField>
        <dataField dataType="Long" name="SortLnu">
          <value>1</value>
          <formattedValue language="de">1</formattedValue>
        </dataField>
        <vocabularyReference name="PublicationVoc" id="62649" instanceName="ObjPublicationVgr">
          <vocabularyReferenceItem id="4491690" name="Nein">
            <formattedValue language="de">Nein</formattedValue>
          </vocabularyReferenceItem>
        </vocabularyReference>
        <vocabularyReference name="TypeVoc" id="62650" instanceName="ObjPublicationTypeVgr">
          <vocabularyReferenceItem id="2600647" name="Daten freigegeben für SMB-digital">
            <formattedValue language="de">Daten freigegeben für SMB-digital</formattedValue>
          </vocabularyReferenceItem>
        </vocabularyReference>
      </repeatableGroupItem>
    </repeatableGroup>
    """


class FreigabeJa:
    def Input(self):
        groups = {
            # "Instrumente-red.Teile": 467399,
            "online Instrumente": 467397
        }
        return groups

    def loop(self):
        """
        loop thru objects in the results
        """
        return "/m:application/m:modules/m:module[@name = 'Object']/m:moduleItem"

    def search(self, Id, limit=-1):
        """
        We're trying to find records of objects that .
        - are members in certain groups
        - not Primärverpackung
        """
        query = Search(module="Object", limit=limit)
        # query.AND()
        query.addCriterion(
            operator="equalsField",
            field="ObjObjectGroupsRef.__id",
            value=str(Id),  # using voc id
        )
        # query.addCriterion(
        #    operator="notEqualsField",  # notEqualsTerm
        #    field="ObjPublicationGrp.TypeVoc",
        #    value="2600647",  # use id? Daten freigegeben für SMB-digital
        # )
        query.addField(field="ObjPublicationGrp")
        query.addField(field="ObjPublicationGrp.repeatableGroupItem")
        query.addField(field="ObjPublicationGrp.PublicationVoc")
        query.addField(field="ObjPublicationGrp.TypeVoc")
        query.addField(field="ObjPublicationGrp.NotesClb")
        query.addField(field="ObjPublicationGrp.ModifiedDateDat")
        query.addField(field="ObjPublicationGrp.ModifiedByTxt")
        query.print()
        query.validate(mode="search")
        return query

    def onItem(self):
        return self.setFreigabeJa

    def setFreigabeJa(self, *, itemN, user: str) -> dict:
        """
        if SMB-Freigabe:
            if Freigabe=Ja -> set it to Nein
            if Freigabe=Nein -> do nothing
        else:
            make a new Freigabe=Nein
        """
        rGrpItemL = itemN.xpath(
            """m:repeatableGroup[
                @name='ObjPublicationGrp'
            ]/m:repeatableGroupItem[
                m:vocabularyReference[
                    @name = 'TypeVoc'
                ]/m:vocabularyReferenceItem[
                    @id = '2600647'
                ]
            ]""",
            namespaces=NSMAP,
        )  # SMB-Freigabe

        # print(rGrpItemL)

        # it's technically possible to have multiple SMB-Freigaben...
        # although that should not happen
        if len(rGrpItemL) > 0:
            return self._changeFreigabeJa(itemN=itemN, user=user)
        else:
            return self._mkNewFreigabeJa(itemN=itemN, user=user)

    def _changeFreigabeJa(self, *, itemN, user: str) -> dict:
        objId = itemN.xpath("@id")[0]
        today = datetime.date.today()
        mtype = "Object"
        print("   _changeFreigabeJa")
        # SMB-Digital
        refId = itemN.xpath(
            """m:repeatableGroup[
                @name='ObjPublicationGrp'
            ]/m:repeatableGroupItem[
                m:vocabularyReference/m:vocabularyReferenceItem[
                    @id = '2600647'
                ]
            ]/@id""",
            namespaces=NSMAP,
        )[0]

        print(f"  refId {refId}")

        try:
            freigabeId = int(
                itemN.xpath(
                    f"""m:repeatableGroup[
                    @name='ObjPublicationGrp'
                ]/m:repeatableGroupItem/
                    m:vocabularyReference[@name = 'PublicationVoc'
                ]/m:vocabularyReferenceItem/@id""",
                    namespaces=NSMAP,
                )[0]
            )
        except:
            freigabeId = 0

        print(f"  freigabeId = {freigabeId}")

        """
        If we DONT re-generate a new ObjPublicationGrp, but just change an existing one
        we do this to not potentially overwrite other fields that I haven't checked for. 
        
        So which values do we want to change
        1) dataField: ModifiedDateDat
        2) dataField: ModifiedByTxt
        3) dataField: NotesClb
        4) vocRefItem: PublicationVoc
        
        We will just assume that any of these values may not yet exist, so we test first 
        if they exist, create them or change them.
        
        if ModifiedDateDat:
            change_value(new_value)
        else:
            new_field(new_value)

        docN, contextN, new_value
        
        crud: create, read, update, delete
        
        read(doc, context, field)
        
        create_or_update
        
        while vocRefItem: TypeVoc remains as is.
        """

        bemerkung2 = "MDVOS Revision der Instrumente"

        if freigabeId != jaId:
            # dont do anything if already ja
            print("  Freigabe != Ja")
            # WARNING: regenerating instead of changing values!
            xml = f"""
                <application xmlns="http://www.zetcom.com/ria/ws/module">
                    <modules>
                        <module name="Object">
                            <moduleItem id="{objId}">
                                <repeatableGroup name="ObjPublicationGrp">
                                    <repeatableGroupItem id="{refId}">
                                        <dataField dataType="Date" name="ModifiedDateDat">
                                           <value>{today}</value>
                                        </dataField>
                                        <dataField dataType="Varchar" name="ModifiedByTxt">
                                           <value>{user}</value>
                                        </dataField>
                                        <dataField dataType="Clob" name="NotesClb">
                                            <value>{bemerkung2}</value>
                                        </dataField>
                                        <vocabularyReference 
                                            name="PublicationVoc" 
                                            id="62649" 
                                            instanceName="ObjPublicationVgr">
                                            <vocabularyReferenceItem id="{jaId}"/>
                                        </vocabularyReference>
                                        <vocabularyReference 
                                            name="TypeVoc" 
                                            id="62650" 
                                            instanceName="ObjPublicationTypeVgr">
                                            <vocabularyReferenceItem id="2600647"/>
                                        </vocabularyReference>
                                    </repeatableGroupItem>
                                </repeatableGroup>
                            </moduleItem>
                        </module>
                    </modules>
                </application>
            """

            # print(xml)
            payload = {
                "type": "updateRepeatableGroup",
                "module": mtype,
                "id": objId,
                "repeatableGroup": "ObjPublicationGrp",
                "xml": xml,
                "success": f"{mtype} {objId}: changed SMBfreigabe to Ja",
                "refId": refId,
            }
            return payload
        # else: return None

    def _mkNewFreigabeJa(self, *, itemN, user: str) -> dict:
        Id = itemN.xpath("@id")[0]
        today = datetime.date.today()
        mtype = "Object"
        print("   mk new Freigabe nein")

        bemerkung = "redundantes Teil"
        bemerkung2 = "MDVOS Revision der Instrumente"

        # should be handled automatically

        xml = f"""
            <application xmlns="http://www.zetcom.com/ria/ws/module">
              <modules>
                <module name="{mtype}">
                  <moduleItem id="{Id}">
                    <repeatableGroup name="ObjPublicationGrp">
                        <repeatableGroupItem>
                            <dataField dataType="Date" name="ModifiedDateDat">
                               <value>{today}</value>
                            </dataField>
                            <dataField dataType="Varchar" name="ModifiedByTxt">
                               <value>{user}</value>
                            </dataField>
                            <dataField dataType="Clob" name="NotesClb">
                                <value>{bemerkung2}</value>
                            </dataField>
                            <vocabularyReference name="PublicationVoc" id="62649" instanceName="ObjPublicationVgr">
                                <vocabularyReferenceItem id="{jaId}"/>
                            </vocabularyReference>
                            <vocabularyReference name="TypeVoc" id="62650" instanceName="ObjPublicationTypeVgr">
                                <vocabularyReferenceItem id="2600647"/>
                            </vocabularyReference>
                        </repeatableGroupItem>
                    </repeatableGroup>
                  </moduleItem>
                </module>
              </modules>
            </application>
        """

        payload = {
            "type": "createRepeatableGroup",
            "module": mtype,
            "id": Id,
            "repeatableGroup": "ObjPublicationGrp",
            "xml": xml,
            "success": f"{mtype} {Id}: set object smbfreigabe Ja",
        }
        return payload

    #
    # helper
    #

    # unused atm
    def completeForUpload(self, *, mtype, moduleItem):
        """
        receive a single moduleItem as lxml fragment, wrap it into a complete document and
        turn it into upload form.
        """

        outer = f"""
        <application xmlns="http://www.zetcom.com/ria/ws/module">
            <modules>
                <module name="{mtype}">
                </module>
            </modules>
        </application>
        """
        ET = etree.fromstring(outer)
        moduleN = ET.xpath("//m:module", namespaces=NSMAP)[0]
        moduleN.append(moduleItem)
        m = Module(tree=ET)
        m.clean()
        m.uploadForm()
        m.toFile(path="debug.xml")
        xml = m.toString()
        xml.encode()  # force UTF8
        return xml
