"""
For the objects of one group, SMB-approve the Standardbild of each object
(i.e. set SMB-digital = Ja on the Multimedia record that the object marks as
its Standardbild).

    mpReplace1 -j FreigabeStandardbild        # dry run, shows what would change
    mpReplace1 -j FreigabeStandardbild -a     # actually writes

Only set the freigabe if the asset does not have an SMB freigabe yet, so an
existing Nein (or Ja) is left alone. Assets that do have an SMB freigabe are
skipped, never changed -- same rule as DigiP.

How the selection works

The Standardbild marker is not a field of the Multimedia record, it is an
attribute of the link between object and asset: on the Object it lives in
ObjMultimediaRef/moduleReferenceItem/dataField[@name='ThumbnailBoo'], and the
Multimedia module shows the same link from its side as
MulObjectRef/moduleReferenceItem/dataField[@name='ThumbnailBoo'].

So we search the Multimedia module for the assets of the objects in the group
(one query, same criterion AssetAndrea uses) and test the two conditions
client-side:

    (a) it is the Standardbild of an object  -> ThumbnailBoo = true
    (b) it has no SMB-freigabe yet           -> no MulApprovalGrp/TypeVoc
                                                 SMB-digital

A Multimedia search response carries MulObjectRef with the ThumbnailBoo
dataField by default (no addField needed, confirmed on a real response: 2000 of
3000 multimedia items in a full-record search carry MulObjectRef, 1901 of those
carry the dataField). Selecting only ThumbnailBoo = true in the query itself was
tried before and is left disabled -- see the commented-out criterion in
AssetDennis and the commented-out addField in getAttachments -- so the test
happens here, client-side.

No payload is produced for an asset that is neither the Standardbild nor
without freigabe; the replacer just counts what it would write.
"""

from mpapi.constants import NSMAP
from mpapi.search import Search

from MpApi.Replace.Plugins.DigiP import DigiP


class FreigabeStandardbild(DigiP):
    def Input(self) -> dict:
        return {"Gruppe 1258399": "1258399"}

    def loop(self) -> str:
        return "/m:application/m:modules/m:module[@name = 'Multimedia']/m:moduleItem"

    def search(self, Id, limit=-1):
        """
        Assets of the objects in one group.

        Same criterion as AssetAndrea: the group membership is taken from the
        object side of the reference.

        A single criterion goes flat under <expert>; Zetcom's search xsd wants
        at least two operands inside <and>, so wrapping one criterion in a
        conjunction does not validate.
        """
        query = Search(module="Multimedia", limit=limit)
        query.addCriterion(
            operator="equalsField",
            field="MulObjectRef.ObjObjectGroupsRef.__id",
            value=str(Id),
        )
        query.validate(mode="search")
        return query

    def onItem(self):
        return self.setStandardbildFreigabe  # returns a callback

    def setStandardbildFreigabe(self, *, itemN, user: str) -> dict | None:
        """
        Called for every Multimedia item in the results. Returns a payload for
        the replacer or None when the asset is left alone.
        """
        Id = itemN.xpath("@id")[0]  # multimedia Id
        module = "Multimedia"

        if not self._is_standardbild(itemN=itemN):
            print(f"  {module} {Id}: not a Standardbild, skipping")
            return None

        if self._has_smb_freigabe(itemN=itemN):
            print(f"  {module} {Id}: SMB-Freigabe exists already, skipping")
            return None

        return self.create_Freigabe(module=module, Id=Id, user=user)

    #
    # helper
    #

    def _is_standardbild(self, *, itemN) -> bool:
        """
        Is this asset the Standardbild of one of its objects?

        The marker sits on the object side of the reference, which a Multimedia
        response carries as MulObjectRef. The dataField is absent when the
        asset is not the Standardbild, so an absent field is a no.
        """
        xpath = """
            .//m:moduleReference[
                @name = 'MulObjectRef'
            ]/m:moduleReferenceItem[
                m:dataField[@name = 'ThumbnailBoo'][m:value = 'true']
            ]"""
        return len(itemN.xpath(xpath, namespaces=NSMAP)) > 0

    def _has_smb_freigabe(self, *, itemN) -> bool:
        """
        Does this asset carry an SMB freigabe already, Ja or Nein?

        Both are left alone, only assets without any SMB-freigabe get one.
        """
        xpath = """
            .//m:repeatableGroup[
                @name = 'MulApprovalGrp'
            ]/m:repeatableGroupItem[
                m:vocabularyReference[
                    @name = 'TypeVoc'
                ]/m:vocabularyReferenceItem[
                    @id = '1816002' or @name = 'SMB-digital'
                ]
            ]"""
        return len(itemN.xpath(xpath, namespaces=NSMAP)) > 0
