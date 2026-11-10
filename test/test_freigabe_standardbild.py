"""
Offline tests for the FreigabeStandardbild plugin.

The structure of the fixture is copied from a real Multimedia search response;
the ids are made up so no production data is committed. What matters here is
the decision: only an asset that is the Standardbild of an object *and* has no
SMB freigabe yet produces a payload.
"""

from MpApi.Replace.Plugins.FreigabeStandardbild import FreigabeStandardbild
from mpapi.constants import NSMAP
from mpapi.module import Module

XML = """
<application xmlns="http://www.zetcom.com/ria/ws/module">
  <modules>
    <module name="Multimedia">
      <moduleItem id="8000001" hasAttachments="true">
        <composite name="MulReferencesCre">
          <compositeItem seqNo="0">
            <moduleReference name="MulObjectRef" targetModule="Object" multiplicity="M:N" size="1">
              <moduleReferenceItem moduleItemId="9000001" seqNo="0">
                <formattedValue language="de">Objekte: 1</formattedValue>
                <dataField dataType="Boolean" name="ThumbnailBoo">
                  <value>true</value>
                  <formattedValue language="de">ja</formattedValue>
                </dataField>
              </moduleReferenceItem>
            </moduleReference>
          </compositeItem>
        </composite>
      </moduleItem>
      <moduleItem id="8000002" hasAttachments="true">
        <composite name="MulReferencesCre">
          <compositeItem seqNo="0">
            <moduleReference name="MulObjectRef" targetModule="Object" multiplicity="M:N" size="1">
              <moduleReferenceItem moduleItemId="9000002" seqNo="0">
                <dataField dataType="Boolean" name="ThumbnailBoo">
                  <value>true</value>
                </dataField>
              </moduleReferenceItem>
            </moduleReference>
          </compositeItem>
        </composite>
        <repeatableGroup name="MulApprovalGrp" size="1">
          <repeatableGroupItem id="7000001">
            <vocabularyReference name="TypeVoc" id="58635" instanceName="MulApprovalTypeVgr">
              <vocabularyReferenceItem id="1816002" name="SMB-digital" />
            </vocabularyReference>
            <vocabularyReference name="ApprovalVoc" id="58634" instanceName="MulApprovalVgr">
              <vocabularyReferenceItem id="4160028" name="Nein" />
            </vocabularyReference>
          </repeatableGroupItem>
        </repeatableGroup>
      </moduleItem>
      <moduleItem id="8000003" hasAttachments="true">
        <composite name="MulReferencesCre">
          <compositeItem seqNo="0">
            <moduleReference name="MulObjectRef" targetModule="Object" multiplicity="M:N" size="1">
              <moduleReferenceItem moduleItemId="9000003" seqNo="0">
                <dataField dataType="Boolean" name="ThumbnailBoo">
                  <value>true</value>
                </dataField>
              </moduleReferenceItem>
            </moduleReference>
          </compositeItem>
        </composite>
        <repeatableGroup name="MulApprovalGrp" size="1">
          <repeatableGroupItem id="7000002">
            <vocabularyReference name="TypeVoc" id="58635" instanceName="MulApprovalTypeVgr">
              <vocabularyReferenceItem id="1816002" name="SMB-digital" />
            </vocabularyReference>
            <vocabularyReference name="ApprovalVoc" id="58634" instanceName="MulApprovalVgr">
              <vocabularyReferenceItem id="4160027" name="Ja" />
            </vocabularyReference>
          </repeatableGroupItem>
        </repeatableGroup>
      </moduleItem>
      <moduleItem id="8000004" hasAttachments="true">
        <composite name="MulReferencesCre">
          <compositeItem seqNo="0">
            <moduleReference name="MulObjectRef" targetModule="Object" multiplicity="M:N" size="1">
              <moduleReferenceItem moduleItemId="9000004" seqNo="0">
                <dataField dataType="Boolean" name="ThumbnailBoo">
                  <value>false</value>
                </dataField>
              </moduleReferenceItem>
            </moduleReference>
          </compositeItem>
        </composite>
      </moduleItem>
      <moduleItem id="8000005" hasAttachments="false">
        <composite name="MulReferencesCre">
          <compositeItem seqNo="0">
            <moduleReference name="MulObjectRef" targetModule="Object" multiplicity="M:N" size="1">
              <moduleReferenceItem moduleItemId="9000005" seqNo="0">
                <dataField dataType="Boolean" name="ThumbnailBoo">
                  <value>true</value>
                </dataField>
              </moduleReferenceItem>
            </moduleReference>
          </compositeItem>
        </composite>
      </moduleItem>
    </module>
  </modules>
</application>
"""


def itemN(Id):
    """the moduleItem with the given id, as the replacer would hand it over"""
    m = Module(xml=XML)
    return m.xpath(
        f"/m:application/m:modules/m:module[@name = 'Multimedia']/m:moduleItem[@id = '{Id}']"
    )[0]


def test_input():
    plugin = FreigabeStandardbild()
    assert plugin.Input() == {"Gruppe 1258399": "1258399"}


def test_loop_selects_multimedia():
    plugin = FreigabeStandardbild()
    assert (
        plugin.loop()
        == "/m:application/m:modules/m:module[@name = 'Multimedia']/m:moduleItem"
    )


def test_search_validates():
    plugin = FreigabeStandardbild()
    query = plugin.search(Id="1258399")
    query.validate(mode="search")
    assert "MulObjectRef.ObjObjectGroupsRef.__id" in query.toString()
    assert "1258399" in query.toString()


def test_standardbild_without_freigabe_is_approved():
    plugin = FreigabeStandardbild()
    payload = plugin.setStandardbildFreigabe(itemN=itemN("8000001"), user="tester")

    assert payload["type"] == "createRepeatableGroup"
    assert payload["module"] == "Multimedia"
    assert payload["id"] == "8000001"
    assert payload["repeatableGroup"] == "MulApprovalGrp"

    # the payload has to be a valid upload document
    Module(xml=payload["xml"]).validate()
    # approval type SMB-digital and approval Ja
    assert 'id="1816002"' in payload["xml"]
    assert 'id="4160027"' in payload["xml"]
    assert "tester" in payload["xml"]


def test_standardbild_with_freigabe_nein_is_left_alone():
    plugin = FreigabeStandardbild()
    assert plugin.setStandardbildFreigabe(itemN=itemN("8000002"), user="tester") is None


def test_standardbild_with_freigabe_ja_is_left_alone():
    plugin = FreigabeStandardbild()
    assert plugin.setStandardbildFreigabe(itemN=itemN("8000003"), user="tester") is None


def test_nicht_standardbild_is_left_alone():
    plugin = FreigabeStandardbild()
    assert plugin.setStandardbildFreigabe(itemN=itemN("8000004"), user="tester") is None


def test_asset_without_object_reference_is_left_alone():
    """no MulObjectRef at all: not the Standardbild of anything we know of"""
    plugin = FreigabeStandardbild()
    m = Module(xml=XML)
    raw = m.xpath(
        "/m:application/m:modules/m:module[@name='Multimedia']/m:moduleItem[@id='8000005']"
    )[0]
    for ref in raw.xpath(
        ".//m:moduleReference[@name='MulObjectRef']", namespaces=NSMAP
    ):
        ref.getparent().remove(ref)
    assert plugin.setStandardbildFreigabe(itemN=raw, user="tester") is None
