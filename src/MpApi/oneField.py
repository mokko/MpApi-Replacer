"""
    Perhaps we need a new replacer. Similar command line interface
    
    replacer -v --version
    replacer -h --help
    -l --lazy : read search results from a file (functions as a cache)
    -a --act: actually do the changes
    -j --job: job name
    -l --limit: limit number of records
    
    - executes a saved query
    - saves resulting xml on disk for debugging
    - loop thru results
    - query one field e.g. Asset.Typ
    - replace one value with another online by executing
        client.updateField (mtype=mtype, ID=ID, dataField="FieldName", value="dfdfd")
        mtype and ID comes from search results
        current_value
        new_value
        
    changes something: e.g.
        replace "Scan" in Asset.Typ with "Karteikarte" 
        
    We typically want to be conservative, e.g. not blindly overwrite anything, 
    So perhaps we replace only specific values as in s/old_value/new_value.
    
    config file. Use toml?
    savedQuery: 1233
    field: ObjObjectNumberTxt
    old_value: Dia
    new_value: Scan

    systemField -> except __orgUnit makes no sense to change them
    dataField
    virtualField -> cant be changed

    <vocabularyReference name="MulTypeVoc" id="30341" instanceName="MulTypeVgr">
      <vocabularyReferenceItem id="31041" name="image">
        <formattedValue language="de">Digitale Aufnahme</formattedValue>
      </vocabularyReferenceItem>
    </vocabularyReference>

    <vocabularyReference name="MulTypeVoc" instanceName="MulTypeVgr">
      <vocabularyReferenceItem id="31041"/>
    </vocabularyReference>
    
    Scan = 1816145
    
"""

import argparse
from lxml import etree
from mpapi.client import MpApi
from mpapi.module import Module
from pathlib import Path
import sys
import tomllib

NSMAP = {
    "m": "http://www.zetcom.com/ria/ws/module",
    "o": "http://www.zetcom.com/ria/ws/module/orgunit",
}

credentials = "credentials.py"

if Path(credentials).exists():
    with open(credentials) as f:
        exec(f.read())


class OneFieldReplacer:
    def __init__(
        self,
        *,
        act: bool = False,
        baseURL: str,
        conf: str = "oneField.toml",
        job: str,
        lazy: bool = False,
        limit: int = -1,
        pw: str,
        user: str,
    ):
        self.act = act
        self.job = job
        self.lazy = lazy
        self.limit = limit
        self.ria = MpApi(baseURL=baseURL, user=user, pw=pw)

        with open(conf, "rb") as f:
            conf = tomllib.load(f)

        self.conf = conf[job]
        for required in ["field", "module", "replace", "savedQuery", "search"]:
            if not required in self.conf:
                raise Exception(
                    f"ERROR: Required configuration value '{required}' missing!"
                )

    def search(self):
        print("* Getting search results")
        ID = self.conf["savedQuery"]
        fn = f"savedQuery-{ID}.xml"
        if self.lazy:
            print(f"* Getting search_results from file cache '{fn}'")
            m = Module(file=fn)
        else:
            print(f" query ID {ID} {self.conf['module']}")
            m = self.ria.runSavedQuery3(
                ID=ID, Type=self.conf["module"], limit=self.limit
            )
            print(f"* writing results to {fn}")
            m.toFile(path=fn)  # overwrites old files
        return m

    def replace(self, *, search_result: Module) -> None:
        #
        # first step is the loop
        #

        # <vocabularyReference name="MulTypeVoc" id="30341" instanceName="MulTypeVgr">
        #  <vocabularyReferenceItem id="31041" name="image">
        #    <formattedValue language="de">Digitale Aufnahme</formattedValue>
        #  </vocabularyReferenceItem>
        # </vocabularyReference>
        # we want to include the search value here to look only thru records/items with
        # matching value
        mtype = self.conf["module"]
        field = self.conf["field"]

        xpath = f"""
            /m:application/m:modules/m:module[
                @name = '{mtype}'
            ]/m:moduleItem[
                m:vocabularyReference[
                    @name='MulTypeVoc'
                ]/m:vocabularyReferenceItem[
                    @id = '31041'
                ]
            ]"""  # 31041 = Digitale Aufnahme

        for itemN in search_result.xpath(xpath):
            return self._perItem(itemN)

    def _perItem(self, itemN):
        """
        Process each individual item (=record), expects itemN as a node

        This is the second step of the actual replacement process.

        As usual i have trouble with the ria (speciication), so I dont know which
        endpoint to use. For posterity, I want to change a simple value in a
        vocabularyReference.

        Options are:
        (a) update the whole record -> updateItem
        (b) update a single field, but unclear if zetcom treats vocRef as field
             -> updateFieldInGroup, seems very unlikely
        (c) update whole rGrp or rGrpItem -> updateRepeatableGroup

        Let's write this method so that I document my faile attempts
        """

        mtype = self.conf["module"]
        field = self.conf["field"]
        mulId = itemN.xpath("@id")[0]  # there can be only one
        refName = itemN.xpath("m:vocabularyReference/@name", namespaces=NSMAP)[0]
        refId = itemN.xpath("m:vocabularyReference/@id", namespaces=NSMAP)[0]
        new_id = "1816145"  # let's use strings consistently although content is int
        print(f"mtype {mtype} mulId {mulId} vocRefId {refId} refName {refName}")

        # self._updateFieldInGroup(mtype=mtype, mulId=mulId, refName=refName, refId=refId, new_id=new_id)

        # self._update_rGrpItem3(
        #    mtype=mtype, mulId=mulId, refName=refName, refId=refId, refItemId_new=refItemId_new
        # )

        # self._updateRepeatableGroup(mtype=mtype, mulId=mulId, refName=refName, refId=refId, new_id=new_id)

        return self._updateItem(
            mtype=mtype,
            mulId=mulId,
            refName=refName,
            refId=refId,
            new_id=new_id,
            itemN=itemN,
        )

    def _updateItem(
        self, *, mtype: str, mulId: int, refName: str, refId: int, new_id: int, itemN
    ):
        """
        First attempt. Let's test module's upload_form and see if we can update an
        existing record
        """
        m = Module(tree=itemN)
        # m.uploadForm()
        request = self.ria.updateItem2(mtype="Multimedia", ID=mulId, data=m)
        print(request)

    def _toString(self, node) -> None:
        return etree.tostring(node, pretty_print=True, encoding="unicode")

    def _updateFieldInGroup(self, *, mtype, mulId, refName, refId, new_id):
        """
        This endpoint seems to be designed to change a dataField in a rGrpItem. Not the
        case here. And attempt to adopt to vocabularyReference fails with 500 bad request.
        """
        xml = f"""
            <application xmlns="http://www.zetcom.com/ria/ws/module">
              <modules>
                <module name="{mtype}">
                  <moduleItem id="{mulId}">
                    <vocabularyReference name="{refName}" id="{refId}" instanceName="MulTypeVgr">
                      <vocabularyReferenceItem id="{new_id}"/>
                    </vocabularyReference>
                  </moduleItem>
                </module>
              </modules>
            </application>"""
        m = Module(xml=xml)
        m.validate()
        print(xml)
        r = self.ria.updateFieldInGroup(
            module=mtype,
            id=mulId,
            referenceId=int(refId),
            dataField="vocabularyReferenceItem",
            repeatableGroup=refName,
            xml=xml,
        )

        print(r)

    def _updateRepeatableGroup(self, *, mtype, mulId, refName, refId, new_id):
        """
        Zetcom specification is unclear if this endpoint is designed to update only a
        item in a rGrp or the whole rGrp, but either way I am not able to use it to
        update a vocRefItem.
        """
        xml = f"""
            <application xmlns="http://www.zetcom.com/ria/ws/module">
              <modules>
                <module name="{mtype}">
                  <moduleItem id="{mulId}">
                    <vocabularyReference name="{refName}" id="{refId}" instanceName="MulTypeVgr">
                      <vocabularyReferenceItem id="{new_id}"/>
                    </vocabularyReference>
                  </moduleItem>
                </module>
              </modules>
            </application>"""
        m = Module(xml=xml)
        m.validate()
        print(xml)
        r = self.ria.updateRepeatableGroup(
            module=mtype,
            id=mulId,
            referenceId=int(refId),
            repeatableGroup=refName,
            xml=xml,
        )

        print(r)

    def _update_rGrpItem3(self, *, mtype, mulId, refName, refId, refItemId_new):
        """This variant uses a different method, but ultimately the same endpoint as
        _updateRepeatableGroup"""

        xml = f"""
            <application xmlns="http://www.zetcom.com/ria/ws/module">
              <modules>
                <module name="{mtype}">
                  <moduleItem id="{mulId}">
                    <vocabularyReference name="{refName}" id="{refId}" instanceName="MulTypeVgr">
                      <vocabularyReferenceItem id="{refItemId_new}"/>
                    </vocabularyReference>
                  </moduleItem>
                </module>
              </modules>
            </application>"""
        m = Module(xml=xml)
        m.validate()
        print(xml)
        r = self.ria.updateRepeatableGroupItem3(
            mtype=mtype,
            ID=int(mulId),
            referenceId=int(refId),
            repeatableGroup=refName,
            xml=xml,
        )

        print(r)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Command line frontend for Replace.py")
    parser.add_argument(
        "-l",
        "--lazy",
        help="lazy modes reads search results from a file cache, for debugging",
        action="store_true",
    )
    parser.add_argument(
        "-a",
        "--act",
        help="include action, without it only show what would be changed",
        action="store_true",
    )
    parser.add_argument(
        "-j", "--job", help="load a plugin and use that code", required=True
    )
    parser.add_argument(
        "-L", "--Limit", help="set limit for initial search", default="-1"
    )
    args = parser.parse_args()
    replacer = OneFieldReplacer(
        act=args.act,
        baseURL=baseURL,
        job=args.job,
        lazy=args.lazy,
        pw=pw,
        user=user,
    )
    m = replacer.search()
    replacer.replace(search_result=m)
