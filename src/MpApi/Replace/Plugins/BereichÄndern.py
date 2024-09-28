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


class Bereich_Ändern:
    def Input(self) -> dict:
        return {"group_id": "778398"}

    def loop(self):
        """
        loop thru objects in the results
        """
        moduleType = "Object"  # later Multimedia
        return f"/m:application/m:modules/m:module[@name = '{moduleType}']/m:moduleItem"

    def search(self, Id: int, limit: int = -1) -> Search:
        query = Search(module="Object", limit=limit)
        query.AND()
        query.addCriterion(
            operator="equalsField",  # notEqualsTerm
            field="__orgUnit",  # __orgUnit is not allowed in Zetcom's own search.xsd
            value="EMAllgemein",
        )
        query.addCriterion(
            operator="equalsField",
            field="ObjObjectGroupsRef.__id",  # ObjCurrentLocationVoc
            value=str(Id),  # using voc id
        )
        q.addField(field="__orgUnit")

        # query.addCriterion(
        # operator="equalsField",
        # field="MulObjectRef.ObjObjectGroupsRef.__id",
        # value="31393",  # Gruppe
        # )
        print(query.toFile(path="query.xml"))
        query.validate(mode="search")
        return query

    def onItem(self) -> callable:
        return self.change_bereich  # returns a callback

    def change_bereich(self, *, itemN, user: str) -> None | dict:
        """
        We're inside a moduleItem here
        """
        Id = itemN.xpath("@id")[0]  # asset Id
        module = "Object"

        payload = {
            "module": "updateField",
            "module": module,
            "id": Id,
            "datafield": "__orgUnit",
            "value": "AKuArchivSSOZ",
            "success": f"{module} {Id}: set Bereich zu AKuArchivSSOZ",
        }

        return payload
