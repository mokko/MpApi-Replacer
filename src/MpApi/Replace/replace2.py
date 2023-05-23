"""
    Perhaps we need a new replacer. This one takes saved queries as input and only
    replaces one field. Maybe we can call that atomic replacing. Similar command line 
    interface as replacer1.

    It's very possible that RIA will let me only act on certain fields and not on others.
    I assume I can't change SystemFields.
    
    It should be easy to change dataFields. Am I right to assume that dataFields can only
    0 or 1 value?
    dataFields
 
    conf.toml
    jobname:
        query 12345
        module Object
        field mulTypeVoc
        search 31041 # image
        replace 31042 # fictional
    
    replacer2 -v --version
    replacer2 -h --help
    replacer2
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
import datetime
from lxml import etree
from mpapi.client import MpApi
from mpapi.constants import credentials, NSMAP, parser
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
        self.conf = self._init_conf(fn=conf, job=job)

    def _init_conf(self, *, fn, job):
        with open(fn, "rb") as f:
            conf = tomllib.load(f)

        job_conf = conf[job]
        print(job_conf)
        for required in ["actions", "module", "savedQuery"]:
            if not required in job_conf:
                raise Exception(
                    f"ERROR: Required configuration value '{required}' missing!"
                )

        for action in job_conf["actions"]:  # minimal sanitization
            # job.action = action.strip() how does this work?
            job_conf["actions"][action]["old"] = job_conf["actions"][action][
                "old"
            ].strip()
            job_conf["actions"][action]["new"] = job_conf["actions"][action][
                "new"
            ].strip()
        return job_conf

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

        """
        # We could potentially turn item in application at a later stage
        # then xpath expressions woulds be shorter, not too much gained
        mulId = itemN.xpath("@id")[0]  # there can be only one
        xml = f"""
            <application xmlns="http://www.zetcom.com/ria/ws/module">
                <modules>
                    <module name="{mtype}"/>
                </modules>
            </application>"""
        outer = etree.fromstring(xml, parser)
        moduleN = outer.xpath("/m:application/m:modules/m:module", namespaces=NSMAP)[0]
        moduleN.append(itemN)
        itemM = Module(tree=outer)
        itemM.uploadForm()
        print(f"{mtype} {mulId}")
        for action in self.conf["actions"]:
            old = self.conf["actions"][action]["old"]
            new = self.conf["actions"][action]["new"]
            if mtype == "Multimedia":
                if action == "Typ":
                    self.MulTypeVoc(
                        itemM=itemM, old=old, new=new
                    )  # change data in place
                elif action == "SMB-Freigabe":
                    self.smbapproval(itemM=itemM, old=old, new=new)
                else:
                    raise TypeError(f"Not yet implemented: {action}")
            else:
                raise TypeError(f"Not yet implemented: {action}")

        fn = f"{mtype}-{mulId}.afterReplace.xml"
        print(f"Writing to {fn}")
        itemM.toFile(path=fn)
        itemM.validate()

        if self.act:
            # currently updates even if nothing has changed
            request = self.ria.updateItem2(mtype=mtype, ID=mulId, data=itemM)
            print(f"Status code: {request.status_code}")

    # should probably not be here
    def _toString(self, node) -> None:
        return etree.tostring(node, pretty_print=True, encoding="unicode")

    #
    # public
    #

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
        Loops through all items in the search results calling the actions described
        for the current job (i.e. in the toml config file).
        """

        mtype = self.conf["module"]

        xpath = f"""
            /m:application/m:modules/m:module[
                @name = '{mtype}'
            ]/m:moduleItem"""

        for itemN in results.xpath(xpath):
            self._perItem(itemN=itemN, mtype=mtype)

    def smbapproval(self, *, old: str, new: str, itemM: Module) -> None:
        """
        Rewrite the smb approval. If old == "None", we test that there is no approval
        element and only add smb approal to the record if there was none before.

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

        if old == "None":
            resL = itemM.xpath(
                """/m:application/m:modules/m:module/m:moduleItem/m:repeatableGroup[
                @name = 'MulApprovalGrp'
            ]/m:repeatableGroupItem/m:vocabularyReference[
                @name = 'TypeVoc'
            ]/m:vocabularyReferenceItem[
                @id = '1816002'
            ]"""
            )

            if resL:
                # SMB approval exists already, but user requested that old value is None,
                # so we dont change anything in this record, i.e. return None now
                print(
                    "SMB approval is not None, but None requested, so not changing approval"
                )
                return
            else:
                print("Need to create a new MulApprovalGrp for SMB-Digital")
        elif old == "Ja":
            resL = itemM.xpath(
                """/m:application/m:modules/m:module/m:moduleItem/m:repeatableGroup[
                @name = 'MulApprovalGrp'
            ]/m:repeatableGroupItem/m:vocabularyReference[
                @name = 'TypeVoc'
            ]/m:vocabularyReferenceItem[
                @id = '1816002'
            ]"""
            )

        known_values = {
            "Ja": 4160027,
            "SMB-Digital": 1816002,
        }

        # rGrp=MulApprovalGrp could already exist
        # let's assume at first that MulApprovalGrp doesn't already exist
        if new == "Ja":
            today = datetime.date.today()
            xml = f"""
                <repeatableGroup xmlns="http://www.zetcom.com/ria/ws/module" name="MulApprovalGrp">
                  <repeatableGroupItem> 
                    <dataField dataType="Varchar" name="ModifiedByTxt">
                      <value>EM_SB</value>
                    </dataField>
                    <dataField dataType="Date" name="ModifiedDateDat">
                      <value>{today}</value>
                    </dataField>
                    <vocabularyReference name="TypeVoc" id="58635" instanceName="MulApprovalTypeVgr">
                      <vocabularyReferenceItem id="1816002"/>
                    </vocabularyReference>
                    <vocabularyReference name="ApprovalVoc" id="58634" instanceName="MulApprovalVgr">
                      <vocabularyReferenceItem id="4160027"/>
                    </vocabularyReference>
                  </repeatableGroupItem>
                </repeatableGroup>
            """

            itemN = itemM.xpath("/m:application/m:modules/m:module/m:moduleItem")[0]
            mulApprovalGrp = etree.fromstring(xml, parser)
            itemN.append(mulApprovalGrp)

    def MulTypeVoc(self, *, old: str, new: str, itemM: Module) -> None:
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

        known_values = {
            "3 D": 1816105,
            "Dia": 1816113,
            "Digitale Aufnahme": 31041,
            "Scan": 1816145,
        }

        try:
            old_id = known_values[old]
        except:
            raise TypeError("Error: Unknown MulTypeVoc value '{old}'")

        try:
            new_id = known_values[new]
        except:
            raise TypeError("Error: Unknown MulTypeVoc value '{new}'")

        vocRefItemL = itemM.xpath(
            f"""/m:application/m:modules/m:module/m:moduleItem/m:vocabularyReference[
                @name = 'MulTypeVoc'
            ]/m:vocabularyReferenceItem[
                @id = {old_id}
            ]"""
        )

        if vocRefItemL:
            # only change data if this item actually has the search value
            attribs = vocRefItemL[0].attrib
            attribs["id"] = str(new_id)
            if "name" in attribs:
                del attribs["name"]
        else:
            print(f"MulTypeVoc: search value '{old}' not found")


if __name__ == "__main__":
    pass
