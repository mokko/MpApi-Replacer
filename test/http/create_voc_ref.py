"""
Object records in Hauke's group often have no Objekttyp. So we want to set it
automatically. For that we need to set a vocabularyReference. If I remember
correctly, that is the one thing we haven't been able to do so far.

So in this test file, we'll make some methodologic tests.

Limitation we want to create a new vocRef, not modify an existing one.

From memory, I think I may have only managed to create new vocRef by
updating the whole document.

Hauke's group: 544398
VIII E 4745 ID: 3266561 has

Which endpoints are conceivable?
updateField? dataField

Sachbegriff:
<dataField dataType="Clob" name="ObjTechnicalTermClb">
  <value>Fotografie</value>
</dataField>


<vocabularyReference name="ObjCategoryVoc" id="30349" instanceName="ObjCategoryVgr">
  <vocabularyReferenceItem id="3206624" name="Fotografie">
    <formattedValue language="de">Fotografie</formattedValue>
  </vocabularyReferenceItem>
</vocabularyReference>


"""

from mpapi.client import MpApi
from mpapi.constants import get_credentials

user, pw, baseURL = get_credentials()
module = "Object"
Id = 3266561
Fotografie = 3206624
groupId = 30349
refName = "ObjCategoryVoc"

client = MpApi(baseURL=baseURL, user=user, pw=pw)

xml = f"""
    <application xmlns="http://www.zetcom.com/ria/ws/module">
      <modules>
        <module name="{module}">
          <moduleItem id="{Id}">
            <vocabularyReference name="{refName}" id="{groupId}">
              <vocabularyReferenceItem id="{Fotografie}"/>
            </vocabularyReference>
          </moduleItem>
        </module>
      </modules>
    </application>"""


print(xml)

# r = client.createReferenceN(module=module, id=Id, groupId=groupId, reference=ref, xml=xml)
r = client.createRepeatableGroup(module=module, id=Id, repeatableGroup=refName, xml=xml)
print(r)
