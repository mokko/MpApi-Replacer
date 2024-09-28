"""
DigiP:
- look at asset records for HF Objekte
- only subset that has typ="Digitalisat p"
- set SMBFreigabe for those assets

Interface: I am looking for a decent easy-to-implement interface

    query = plugin.search(limit=1)  # returns search object (which enables us
                                    # select a set of records later). limit parameter is optional
    xpath = plugin.loop()    # returns a string with an xpath expression (which
                             # will be used to loop thru the right moduleItems)
    onItem = plugin.onItem() # returns a callback to a method which is called
                             # inside every selected moduleItem. (It's supposed
                             # make a change on the database upstream.)
    the onItem method is also included in the plugin. I like to refer to it as
    "the payload". But in the code i prefer a more expressive label such as
    setAssetFreigabe.
"""

import datetime
from mpapi.search import Search
from mpapi.constants import NSMAP

changes = 0


class DigiP:
    def Input(self) -> dict:
        return {"locId": "4220557"}

    def loop(self) -> str:
        return "/m:application/m:modules/m:module[@name = 'Multimedia']/m:moduleItem"

    def search(self, Id: int, limit: int = -1) -> Search:
        query = Search(module="Multimedia", limit=limit)
        query.AND()
        query.addCriterion(
            operator="equalsField",
            field="MulObjectRef.ObjCurrentLocationVoc",  # ObjCurrentLocationVoc
            value=Id,  # using voc id
        )
        query.addCriterion(
            operator="equalsField",  # equalsTerm
            field="MulTypeVoc",  # ObjCurrentLocationVoc
            value="4457921",  # using voc id Digitalisat p = 4457921
        )
        query.addCriterion(
            operator="notEqualsField",  # equalsTerm
            field="MulApprovalGrp.TypeVoc",  # ObjCurrentLocationVoc
            value="1816002",  # using vocId SMB-Digital = 1816002
        )
        return query

    def onItem(self) -> callable:
        return self.setAssetFreigabe  # returns a callback

    def setAssetFreigabe(self, *, itemN, user: str) -> None | dict:
        """
        We're inside Multimedia's nodeItem here
        We have already filtered to our hearts delight, so can change
        immediately.
        """
        Id = itemN.xpath("@id")[0]  # asset Id
        module = "Multimedia"
        xpath = f"""
            /m:application/m:modules/m:module[@name='{module}'
        ]/m:moduleItem[@id='{Id}']/m:repeatableGroup[
            @name='MulApprovalGrp'
        ]/m:repeatableGroupItem/m:vocabularyReference[
            @name='TypeVoc'
        ]/m:vocabularyReferenceItem[
            @id = '1816002']"""
        # print(xpath)
        testL = itemN.xpath(xpath, namespaces=NSMAP)

        if len(testL) > 0:
            # print("SMB-Freigabe exists already; no change") # {Id}
            # if there is a SMB-Freigabe already, do nothing
            # print(f"***{testL=}")
            return None
        return self.create_Freigabe(module=module, Id=Id, user=user)

    def create_Freigabe(self, *, module: str, Id: int, user: str) -> dict:
        today = datetime.date.today()
        sort = 1  # unsolved! I suspect it can be None or missing
        print("SMB-Freigabe does not yet exists; setting Freigabe")

        xml = f"""
        <application xmlns="http://www.zetcom.com/ria/ws/module">
          <modules>
            <module name="{module}">
              <moduleItem id="{Id}">
                <repeatableGroup name="MulApprovalGrp">
                    <repeatableGroupItem>
                        <dataField dataType="Varchar" name="ModifiedByTxt">
                            <value>{user}</value>
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
              </moduleItem>
            </module>
          </modules>
        </application>"""

        payload = {
            "type": "createRepeatableGroup",
            "module": module,
            "id": Id,
            "repeatableGroup": "MulApprovalGrp",
            "xml": xml,
            "success": f"{module} {Id}: set asset smbfreigabe",
        }

        return payload
