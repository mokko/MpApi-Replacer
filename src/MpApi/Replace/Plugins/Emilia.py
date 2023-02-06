from MpApi.Replace.Plugins.WestFreigabe import WestFreigabe
from mpapi.search import Search


class Emilia(WestFreigabe):
    def Input(self):
        groups = {
            "Chinesische Sprichwörter": 225397,
            "Ainu": 242397,
            "Hof_und_Folter": 242399,
            "Reispapierbilder_Miniaturen": 308400,
            "Gottheiten": 242398,
        }

        return groups

    def search(self, Id, limit=-1):
        query = Search(module="Object", limit=limit)
        query.AND()
        query.addCriterion(
            operator="equalsField",
            field="ObjObjectGroupsRef.__id",
            value=str(Id),  # using voc id
        )
        query.addCriterion(
            operator="notEqualsField",  # notEqualsTerm
            field="ObjPublicationGrp.TypeVoc",
            value="2600647",  # use id? Daten freigegeben für SMB-digital
        )
        query.addCriterion(
            operator="notEqualsField",  # notEqualsTerm
            field="__orgUnit",  # __orgUnit is not allowed in Zetcom's own search.xsd
            value="EMPrimarverpackungen",  # 1632806EM-Primärverpackungen
        )
        query.addCriterion(
            operator="notEqualsField",  # notEqualsTerm
            field="__orgUnit",
            value="AKuPrimarverpackungen",  # 1632806EM-Primärverpackungen
        )
        query.addField(field="ObjPublicationGrp")
        query.addField(field="ObjPublicationGrp.repeatableGroupItem")
        query.addField(field="ObjPublicationGrp.PublicationVoc")
        query.addField(field="ObjPublicationGrp.TypeVoc")
        # query.print()
        return query
