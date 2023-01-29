"""
    Perhaps we need a new replacer. Similar command line interface
    
    replacer -v --version
    replacer -h --help
    -a --act: actually do the changes
    -c --cache: read search results from a file (functions as a cache, used to be called lazy)
    -j --job: job name
    -l --limit: limit number of records
    
    init
    - loads toml config file with descripion of available/defined jobs
    - executes one of the jobs
    search
    - executes a saved query
    - saves resulting xml on disk for debugging
    - with -c take search results from file cache instead of querying ria again
    replace
    - loop thru results
    - if and only if search value matches old value, replace old value with new one

    It seems like we're updating the whole record anyways. So we need to teach this 
    script the individual fields
        

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
from mpapi.constants import NSMAP, credentials
from mpapi.module import Module
from pathlib import Path
import sys
import tomllib


if Path(credentials).exists():
    with open(credentials) as f:
        exec(f.read())


class ConfigError(Exception):
    pass


class Replace2:
    def __init__(
        self,
        *,
        act: bool = False,
        baseURL: str,
        conf: str = "replace2.toml",
        job: str,
        cache: bool = False,
        limit: int = -1,
        pw: str,
        user: str,
    ):
        self.act = act
        self.job = job
        self.cache = cache
        self.limit = limit
        self.ria = MpApi(baseURL=baseURL, user=user, pw=pw)

        with open(conf, "rb") as f:
            conf = tomllib.load(f)

        self.conf = conf[job]
        for required in ["actions", "module", "savedQuery"]:
            if not required in self.conf:
                raise Exception(
                    f"ERROR: Required configuration value '{required}' missing!"
                )

    def search(self):
        """
        Either make a new query to RIA or return the cached results from previous run
        (in cache mode).

        It's the user's the responsibility to decide when they want to make a new query.

        Returns Module data potentially with many items/records.
        """
        qId = self.conf["savedQuery"]
        fn = f"savedQuery-{qId}.xml"
        if self.cache:
            print(f"* Getting search results from file cache '{fn}'")
            m = Module(file=fn)
        else:
            print(f"* New query ID {qId} {self.conf['module']}")
            m = self.ria.runSavedQuery3(
                ID=qId, Type=self.conf["module"], limit=self.limit
            )
            print(f"* Writing search results to {fn}")
            m.toFile(path=fn)  # overwrites old files
        return m

    def replace(self, *, results: Module) -> None:
        """
        Loops through all items in the search results calling the actions
        described for the current job (i.e. in the toml config file).
        """

        mtype = self.conf["module"]

        xpath = f"""
            /m:application/m:modules/m:module[
                @name = '{mtype}'
            ]/m:moduleItem"""

        for itemN in results.xpath(xpath):
            return self._perItem(itemN=itemN, mtype=mtype)

    def _perItem(self, *, itemN, mtype: str) -> None:
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
        mulId = itemN.xpath("@id")[0]  # there can be only one
        itemM = Module(tree=itemN)
        itemM.uploadForm()
        for action in self.conf["actions"]:
            old = self.conf["actions"][action]["old"]
            new = self.conf["actions"][action]["new"]
            if mtype == "Multimedia":
                if action == "MulTypeVoc":
                    self.MulTypeVoc(
                        itemM=itemM, old_value=old, new_value=new
                    )  # change data in place
                else:
                    raise TypeError(f"Not yet implemented: {action}")
            else:
                raise TypeError(f"Not yet implemented: {action}")
        fn = "afterReplace.temp.xml"
        print(f"Writing to {fn}")
        itemM.toFile(path=fn)

        if self.act:
            request = self.ria.updateItem2(mtype=mtype, ID=mulId, data=itemM)
            print(request)

    def MulTypeVoc(self, *, old_value: str, new_value: str, itemM: Module) -> None:
        """
        Rewrite itemN data according to action described in toml file.

        We assume we get only one item/record of the proper mtype passed here inside of
        itemM.

        itemM should be changed in place, so no return value necessary?

        <vocabularyReference name="MulTypeVoc" id="30341" instanceName="MulTypeVgr">
          <vocabularyReferenceItem id="31041" name="image">
            <formattedValue language="de">Digitale Aufnahme</formattedValue>
          </vocabularyReferenceItem>
         </vocabularyReference>
        we want to include the search value here to look only thru records/items with
        matching value -> not anymore. Let's be more generic
        """

        vocRefItemN = itemM.xpath(
            f"""/m:application/m:modules/m:module/m:moduleItem/m:vocabularyReference[
                @name = 'MulTypeVoc'
            ]/m:vocabularyReferenceItem[
                @id = {old_value}
            ]"""
        )[0]

        attribs = vocRefItemN.attrib
        attribs["id"] = str(new_value)
        if "name" in attribs:
            del attribs["name"]

    # should probably not be here
    def _toString(self, node) -> None:
        return etree.tostring(node, pretty_print=True, encoding="unicode")


if __name__ == "__main__":
    pass
