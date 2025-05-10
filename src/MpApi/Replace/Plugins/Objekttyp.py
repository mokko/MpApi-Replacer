"""
For records without Objekttyp, give them a Objekttyp.

<vocabularyReference name="ObjCategoryVoc" id="30349" instanceName="ObjCategoryVgr">
  <vocabularyReferenceItem id="3206624" name="Fotografie"/>
</vocabularyReference>
"""

from mpapi.search import Search
from lxml import etree
from mpapi.constants import NSMAP
from mpapi.module import Module
from MpApi.Replace.Plugin import Plugin


class Objekttyp(Plugin):
    def Input(self) -> dict:
        group = {"Haukes Gruppe": 544398}
        return group

    def search(self, Id: int, limit: int) -> Search:
        q = Search(module="Object", limit=limit)
        q.addCriterion(
            operator="equalsField",
            field="ObjObjectGroupsRef.__id",
            value=str(Id),  # using voc id
        )
        # Do we want to limit results to certain fields?
        q.addField(field="ObjCategoryVoc")
        q.validate(mode="search")
        return q

    def loop(self) -> str:
        return "/m:application/m:modules/m:module[@name = 'Object']/m:moduleItem"

    def onItem(self) -> callable:
        return self.set_Objekttyp  # returns a callback

    def set_Objekttyp(self, *, itemN, user):
        Id = itemN.xpath("@id")[0]
        module = "Object"

        Typen = {
            "Allgemein": 3206608,
            "Audio": 3206616,
            "Fotografie": 3206624,
            "Musikinstrument": 3206642,
            "Zeichnung": 3206658,
        }

        r = itemN.xpath(
            "m:vocabularyReference[@name='ObjCategoryVoc']", namespaces=NSMAP
        )
        if len(r) == 1:
            # if there is a VerwaltendeInsttution do nothing
            print("Objekttyp exists already!")
            return None
        elif len(r) > 1:
            raise TypeError("Not allowed")

        xml = f"""
            <application xmlns="http://www.zetcom.com/ria/ws/module">
              <modules>
                <module name="{module}">
                  <moduleItem id="{Id}">
                    <vocabularyReference name="ObjCategoryVoc" id="30349" instanceName="ObjCategoryVgr">
                      <vocabularyReferenceItem id="{Typen["Fotografie"]}"/>
                    </vocabularyReference>
                  </moduleItem>
                </module>
              </modules>
            </application>
        """
        print(xml)

        m = Module(xml=xml)
        m.validate()
        print("...validates")

        return {
            "type": "createRepeatableGroup",
            "module": module,
            "id": str(Id),
            "repeatableGroup": "ObjCategoryVoc",
            "xml": xml,
            "success": f"{module} {Id}: set Objekttyp",
        }
