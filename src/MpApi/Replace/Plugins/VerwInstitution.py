"""
If empty set VerwaltendeInsttution for items in group.
"""

from mpapi.search import Search
from lxml import etree
from mpapi.constants import NSMAP
from mpapi.module import Module
from MpApi.Replace.Plugin import Plugin


class VerwInstitution(Plugin):
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
        # query.addField(field="ObjOwnerRef")

        q.validate(mode="search")
        return q

    def loop(self) -> str:
        return "/m:application/m:modules/m:module[@name = 'Object']/m:moduleItem"

    def onItem(self) -> callable:
        return self.set_verwaltende_Institution  # returns a callback

    def set_verwaltende_Institution(self, *, itemN, user):
        Id = itemN.xpath("@id")[0]
        module = "Object"

        Institutions = {"EM": 67678}
        r = itemN.xpath("m:moduleReference[@name='ObjOwnerRef']", namespaces=NSMAP)
        if len(r) == 1:
            # if there is a VerwaltendeInsttution do nothing
            print("Verwaltende Institution exists already!")
            return None
        elif len(r) > 1:
            raise TypeError("Not allowed")

        xml = f"""
            <application xmlns="http://www.zetcom.com/ria/ws/module">
              <modules>
                <module name="{module}">
                  <moduleItem id="{Id}">
                    <moduleReference name="ObjOwnerRef" targetModule="Address"> 
                      <moduleReferenceItem moduleItemId="{Institutions["EM"]}" />
                    </moduleReference>
                  </moduleItem>
                </module>
              </modules>
            </application>
        """

        m = Module(xml=xml)
        m.validate()
        print("...validates")

        return {
            "type": "createRepeatableGroup",
            "module": module,
            "id": str(Id),
            "repeatableGroup": "ObjOwnerRef",
            "xml": xml,
            "success": f"{module} {Id}: set verwaltende Institution",
        }
