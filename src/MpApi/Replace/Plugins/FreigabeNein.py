import datetime
from mpapi.search import Search
from lxml import etree  # type: ignore
from mpapi.module import Module
from mpapi.constants import NSMAP

neinId = 4491690
jaId = 1810139
bemerkung = "nicht freigeben, weil nur Ausstellungsobjekt; wir sind nicht verwaltende Inst. oder die Objektdaten sind schlecht"

"""
    WARNING: This is quick and dirty. I

    For the records in one or more groups, set them to SMB-Freigabe = Nein
    if Freigabe is not already "Nein".

    There are at least two possible cases for the situation
    (a) no SMBfreigabe has been set before -> add a new one
    (b) SMBfreigabe exists already and it's not Nein 
        (probably None or Ja) -> change to Nein.

    Leave records with smbFreigabe = Nein alone.

    "Nein" has the voc ID 4491690
    
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


class FreigabeNein:
    def Input(self):
        groups = {
            "Ausstellungsobjekte ": 509400,
            # "online Instrumente": 467397
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
        query.AND()
        query.addCriterion(
            operator="equalsField",
            field="ObjObjectGroupsRef.__id",
            value=str(Id),  # using voc id
        )
        query.addCriterion(
            operator="equalsField",  # notEqualsTerm
            field="ObjPublicationGrp.PublicationVoc",
            value=str(jaId),  # use id? Daten freigegeben für SMB-digital
        )
        query.addCriterion(
            operator="equalsField",  # notEqualsTerm
            field="ObjPublicationGrp.TypeVoc",
            value=str(2600647),  # Daten freigegeben für SMB-digital
        )
        query.addField(field="ObjPublicationGrp")
        query.addField(field="ObjPublicationGrp.repeatableGroupItem")
        query.addField(field="ObjPublicationGrp.PublicationVoc")
        query.addField(field="ObjPublicationGrp.TypeVoc")
        query.addField(field="ObjPublicationGrp.NotesClb")
        # query.print()
        query.validate(mode="search")
        return query

    def onItem(self):
        return self.setFreigabeNein

    def setFreigabeNein(self, *, itemN, user: str) -> dict:
        """
        if SMB-Freigabe:
            if Freigabe=Ja -> set it to Nein
            if Freigabe=Nein -> do nothing
        else:
            make a new Freigabe=Nein
        """
        rGrpItemL = itemN.xpath(
            """m:repeatableGroup[
            @name='ObjPublicationGrp']/m:repeatableGroupItem[
                    m:vocabularyReference[@name = 'TypeVoc']/
                    m:vocabularyReferenceItem[@id = '2600647']
            ]""",
            namespaces=NSMAP,
        )  # SMB-Freigabe

        # print(rGrpItemL)

        # it's technically possible to have multiple contradicting SMB-Freigaben
        # obviously, we dont want contradicting entries
        # although that should not happen
        if len(rGrpItemL) > 0:
            # if exsting SMB-Freigabe = Ja
            return self._setFreigabeNein(itemN=itemN, user=user)
        else:
            # if no SMB-Freigabe at all
            return self._mkNewFreigabeNein(itemN=itemN, user=user)

    def _setFreigabeNein(self, *, itemN, user: str) -> dict:
        objId = itemN.xpath("@id")[0]
        today = datetime.date.today()
        mtype = "Object"
        print("   _setFreigabeNein")
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

        # dont do anything if already Nein
        # should be implied in search querey, but we can have it twice
        if freigabeId != neinId:
            print("  Freigabe != Nein")
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
                                            <value>{bemerkung}</value>
                                        </dataField>
                                        <vocabularyReference 
                                            name="PublicationVoc" 
                                            id="62649" 
                                            instanceName="ObjPublicationVgr">
                                            <vocabularyReferenceItem id="{neinId}"/>
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
                "success": f"{mtype} {objId}: change SMBfreigabe to Nein",
                "refId": refId,
            }
            return payload
        # else: return None

    def _mkNewFreigabeNein(self, *, itemN, user: str) -> dict:
        Id = itemN.xpath("@id")[0]
        today = datetime.date.today()
        mtype = "Object"
        print("   mk new Freigabe nein")

        # should be handled automatically
        # <dataField dataType="Date" name="ModifiedDateDat">
        #    <value>{today}</value>
        # </dataField>
        # <dataField dataType="Varchar" name="ModifiedByTxt">
        #    <value>EM_MM1</value>
        # </dataField>

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
                                <value>{bemerkung}</value>
                            </dataField>
                            <vocabularyReference name="PublicationVoc" id="62649" instanceName="ObjPublicationVgr">
                                <vocabularyReferenceItem id="{neinId}"/>
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
            "success": f"{mtype} {Id}: set object smbfreigabe",
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
