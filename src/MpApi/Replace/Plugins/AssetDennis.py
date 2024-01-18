"""
Andrea wants to publish a group on SMB-Digital; this script SMB approves all 
assets attached to object records in that group, unless they have 
    SMB-Freigabe = Nein
For a couple secret Yurupari flutes, photos/depictions are not shown.

Fotografen:
look for assets
- Bereich "EM-Am Ethnologie" -> EMAmEthnologie 
- only assets that dont have SMB-Freigabe yet
- belong to objects in group 29636
do
- set SMBFreigabe for those assets

PROBLEM:
- if this script is run multiple times, records obtain muliple freigaben


"""

import datetime

from mpapi.search import Search
from MpApi.Replace.Plugins.DigiP import DigiP


class AssetDennis(DigiP):
    def search(self, Id, limit):
        query = Search(module="Multimedia", limit=-1)
        query.AND()
        # 2nd criteria
        query.addCriterion(
            operator="equalsField",
            field="MulObjectRef.ObjObjectGroupsRef.__id",
            value="604399",  # Uhde Mexiko
        )
        # 2nd criteria: avoid multiple Freigaben for successive runs!
        # query.addCriterion(
        #    operator="notEqualsField",  # equalsTerm
        #    field="MulApprovalGrp.TypeVoc",  # ObjCurrentLocationVoc
        #    value="1816002",  # using vocId SMB-Digital = 1816002
        # )
        # 3rd criteria: only assets with attachment?
        query.addCriterion(
            operator="equalsField",  # equalsTerm
            field="MulObjectRef.ThumbnailBoo",  # ObjCurrentLocationVoc
            value="true",  # using vocId SMB-Digital = 1816002
        )
        print(query.toFile(path="query.xml"))
        query.validate(mode="search")
        return query
