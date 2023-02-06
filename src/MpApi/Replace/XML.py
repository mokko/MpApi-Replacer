"""
    We need to offload some xml logic. But right now not clear exactly what and how
    
    itemN is xml fragment as ET; it has to have incomplete form (moduleItem, not /application).
    
    We save itemN internally in self.et
    
    # two construtors - not really, but almost
    itemM = item.Multimedia(xml=xml)
    itemM = item.Multimedia(et=itemN)
    # internally we save complete xml using /application/modules/module...
    # during construction we check if only one item and only mtype

    mulApprovalGrpN = item.MulApprovalGrp()      # there can be only one MulApprovalGrp, so we return None or one
    item.add_MulApprovalGrp_SMBDigital_Ja()      # creates a new MulApprovalGrp and vocRef SMBDIgital
                                                 # raises if MulApprovalGrp.SMBDigital already exists
                                                 # doesn't raise if MulApprovalGrp exists already
    # I wonder if we have to parameterize anything like this:
    item.set_MulApprovalGrp(type="SMBDigital", freigabe="Ja") # or similar

    I wonder how this interface would overlap with the existing from-scratch-interface in Module

    Can we generize this further?
    item.add_vocRefGrp

    
    
    
"""
from lxml import etree, _element
from mpapi.constants import NSMAP
from typing import Optional

class item.Multimedia: 
    """
    Checks if a node, element or attribute exists and returns it or None (or empty List?) if it doesn't.
    
    Do we hand over itemN or itemM? We return a node in any case, so mulApprvalGrpN
    """
    def MulApprovalGrp(self, itemN) -> Optional[lxml._element]:
    """
        We return MulApprovalGrp if it exists
        <repeatableGroup name="MulApprovalGrp" size="1">
    """
        resL = itemN.xpath(
            """/m:application/m:modules/m:module/m:moduleItem/m:repeatableGroup[
                @name = 'MulApprovalGrp'
            ]""", namespaces=NSMAP)
        return resL


    def MulApprovalGrp_SMBDigital(self, itemN) -> Optional[lxml._element]:
        """
        We return MulApprovalGrp if it has SMB-Digital
        """
        resL = itemN.xpath(
            """/m:application/m:modules/m:module/m:moduleItem/m:repeatableGroup[
                @name = 'MulApprovalGrp'
            ]/m:repeatableGroupItem/m:vocabularyReference[
                @name = 'TypeVoc'
            ]/m:vocabularyReferenceItem[
                @id = '1816002'
            ]""", namespaces=NSMAP)
        return resL


    def MulApprovalGrp_SMBDigital_Ja(self, itemN) -> Optional[lxml._element]:
        """
            <repeatableGroup name="MulApprovalGrp" size="1">
              <repeatableGroupItem id="10159204">
                <vocabularyReference name="TypeVoc" id="58635" instanceName="MulApprovalTypeVgr">
                  <vocabularyReferenceItem id="1816002" name="SMB-digital">
                    <formattedValue language="en">SMB-digital</formattedValue>
                  </vocabularyReferenceItem>
                </vocabularyReference>
                <vocabularyReference name="ApprovalVoc" id="58634" instanceName="MulApprovalVgr">
                  <vocabularyReferenceItem id="4160027" name="Ja">
                    <formattedValue language="en">Ja</formattedValue>
                  </vocabularyReferenceItem>
                </vocabularyReference>
              </repeatableGroupItem>
            </repeatableGroup>
        """
        resL = itemN.xpath("""/m:application/m:modules/m:module/m:moduleItem/m:repeatableGroup[
                @name = 'MulApprovalGrp'
            ][m:repeatableGroupItem/m:vocabularyReference[
                @name = 'TypeVoc'
            ]/m:vocabularyReferenceItem[
                @id = '1816002'
            ]]""", namespaces=NSMAP)
        return resL

class xml_maker
    def add_MulApprovalGrp (self, itemM) -> None:
        """
        receive an item, probably in form of itemM or alternatively as itemN, generate and 
        add some xml. Probably we change itemM in place so return value is free. 
        
        We can raise errors if need be.
        
        We dont need this right now.
        """


    def add_MulApprovalGrp_SMBDigital(self, itemM) -> None:
        """
        
        """

    def add_MulApprovalGrp_SMBDigital_Ja (self, itemM) -> None:
        """
        """

