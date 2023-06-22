"""

Code that is reusable over multiple replacer apps

"""

from lxml import etree
from mpapi.client import MpApi
from mpapi.module import Module
import pprint

try:
    import tomllib  # Python v3.11
except ModuleNotFoundError:
    import tomli as tomllib  # < Python v3.11


# user-facing field names: no space, no period, no slash
RIA_data = {
    "Multimedia": {
        "Anlass": "vocabularyReference:MulShootingReasonVoc",
        "Bereich": {
            "systemField:__orgUnit": {
                "EM-Afrika": "EMAfrika1",
                "EM-Allgemein": "EMAllgemein",
                "EM-Am Archaologie": "EMAmArchaologie",
                "EM-Am Ethnologie": "EMAmEthnologie",
                "EM-Medienarchiv": "EMMedienarchiv",
                "EM-Musikethnologie": "EMMusikethnologie",
            }
        },
        "Datum": "dataField:MulDateTxt",  # Freitext
        "Farbe": "vocabularyReference:MulColorVoc",
        "Format": "vocabularyReference:MulFormatVoc",
        "Freigabe.Freigabe": {
            "repeatableGroup:MulApprovalGrp:ApprovalVoc": {
                "Ja": 4160027,
                "Nein": 4160028,
            }
        },
        "Funktion": {
            "vocabularyReference:MulCategoryVoc": {
                "Audio": 1055742,
                "Arbeitsfoto": 4771972,
                "Video": 5042851,
            },
        },
        "InhAns": "dataField:MulSubjectTxt",
        "MatTech": "vocabularyReference:MulMatTechVoc",
        "Status": "vocabularyReference:MulStatusVoc",
        "TypDetails": "dataField:MulTypeTxt",
        "Typ": "vocabularyReference:MulTypeVoc",
    },
    "Object": {
        "Freigabe.Freigabe": {
            "repeatableGroup:ObjPublicationGrp:PublicationVoc": {
                "Ja": 1810139,
                "Nein": 4491690,
            }
        },
        "Freigabe.Typ": {
            "repeatableGroup:ObjPublicationGrp:TypeVoc": {
                "Daten freigegeben für SMB-digital": 2600647,
            }
        },
    },
}


class BaseApp:
    def __init__(
        self,
        *,
        act: bool = False,
        baseURL: str,
        conf_fn: str,
        cache: bool = False,
        limit: int = -1,
        pw: str,
        user: str,
    ) -> None:
        self.act = act
        self.cache = cache
        self.limit = limit
        self.ria = MpApi(baseURL=baseURL, user=user, pw=pw)
        self.conf = self._init_conf(conf_fn=conf_fn)
        self.conf = self._rewrite_conf(self.conf)
        pprint.pprint(self.conf)
        print(f"Logged in as {user}")

    def replace(self, *, search_results: Module) -> None:
        """
        Loops through all items in the search results and call the actions for the
        current job (i.e. in the toml config file).
        """

        mtype = self.conf["module"]
        IDs = search_results.xpath(
            f"/m:application/m:modules/m:module[@name='{mtype}']/m:moduleItem/@id"
        )

        # to avoid deep copy, so we loop thru one big document with many items
        for ID in IDs:
            self._per_item(doc=search_results, ID=ID)

    def search(self) -> Module:
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

    #
    # public
    #

    def _completeItem(self, *, data: Module, ID: int) -> str:
        """
        Return a single moduleItem wrapped in xml as required by Zetcom.

        Receive the whole document (with many items) and a moduleItem ID and returns a
        complete xml doc as string with only that one moduleItem.

        TODO: Revisit return value. Is str really right? Alternatives are lxml doc
        and Module.
        """
        mtype = data.xpath("/m:application/m:modules/m:module/@name")[0]
        mItemN = data.xpath(
            f"/m:application/m:modules/m:module/m:moduleItem[@id = {ID}]"
        )[0]

        xml = f"""
            <application xmlns="http://www.zetcom.com/ria/ws/module">
                <modules>
                    <module name="{mtype}"/>
                </modules>
            </application>                
        """

        m = Module(xml=xml)
        moduleN = m.xpath("/m:application/m:modules/m:module")[0]
        moduleN.append(mItemN)
        return m.toString()

    def _field2xml(self, node):
        xml = f"""
            <application xmlns="http://www.zetcom.com/ria/ws/module">
                <modules>
                    <module name="{mtype}">
                        <moduleItem id="{ID}"/>
                    </module>
                </modules>
            </application>"""
        doc = etree.XML(xml)
        mItemN = doc.xpath(
            "/m:application/m:modules/m:module/m:moduleItem", namespaces=NSMAP
        )[0]
        mItemN.append(node)
        return m.toString()

    def _init_conf(self, *, conf_fn: str) -> dict:
        with open(conf_fn, "rb") as f:
            conf = tomllib.load(f)

        for required in ["module", "savedQuery", "replace"]:
            if not required in conf:
                raise Exception(
                    f"ERROR: Required configuration value '{required}' missing!"
                )
        return conf

    def _rewrite_conf(self, conf: dict) -> dict:
        """
        Rewrites external conf values with internal RIA ones; also some sanitizing as
        values other than requested ones are dropped.

        The new conf values have different keys, distinguishing between the user-facing
        view (external) and the internal values RIA uses.
        """
        print("Looking up internal conf values")
        new = {}
        new["module"] = conf["module"]
        new["savedQuery"] = conf["savedQuery"]
        new["replace"] = []

        mtype = conf["module"]
        for action in conf["replace"]:
            action2 = {}
            f_ex = action["field"]
            s_ex = action["search"]
            r_ex = action["replace"]
            try:
                RIA_data[mtype][f_ex]
            except KeyError:
                raise SyntaxError(f"ERROR: Unknown external field: {f_ex}")

            try:
                f_in = RIA_data[mtype][f_ex]
            except:
                pass
            if not isinstance(f_in, str):
                try:
                    f_in = list(RIA_data[mtype][f_ex].keys())[0]
                except:
                    raise SyntaxError("Error: f_in not found!")
            print(f"  {f_ex} -> {f_in}")
            action2["f_in"] = f_in
            action2["f_ex"] = f_ex
            action2["s_ex"] = s_ex
            action2["r_ex"] = r_ex
            action2["field"] = [x.strip() for x in f_in.split(":")]
            # print ("  "+str(action2["field"]))
            try:
                action2["s_in"] = RIA_data[mtype][f_ex][f_in][s_ex]
            except KeyError:
                raise SyntaxError(
                    f"ERROR: external search value '{s_ex}' not in {mtype}: {f_ex}"
                )
            except TypeError:
                action2["s_in"] = s_ex
            try:
                action2["r_in"] = RIA_data[mtype][f_ex][f_in][r_ex]
            except KeyError:
                raise SyntaxError(
                    f"ERROR: external replace value '{r_ex}' not in {mtype}: {f_ex}"
                )
            except:
                action2["r_in"] = r_ex

            if action2["field"][0] not in (
                "dataField",
                "repeatableGroup",
                "systemField",
                "vocabularyReference",
            ):
                raise SyntaxError(f"ERROR: Unknown field type: {action2['field'][0]}")

            new["replace"].append(action2)

        return new

    def _parse_conf(self, conf:dict) -> dict:
        """
        This is the new version of the config file parser. Main upshot is that for every 
        record changes in multiple fields can be described.
        
        Keywords
        - filter: narrow down the nodes that are effected by the changes; can be repeated
          to add multiple conditions; adding filters implies a logical AND. Logical OR 
          will not be supported.
        - new: create new nodes where there were none before
        - write: overwrite values in existing nodes; does not send an update if field 
          already has the target value.
          use together with filter or query to achieve a classic search/replace.
        - new_or_write: creates a new element, if there is none or, if it already exists
          set the new target value if that the current value is not yet target value
        
        Example for SMB-Freigabe
        query results in Objects from a certain object group; we want to set Freigabe=Ja
        for all of them. We dont not want to change records that are explictly marked as
        Freigabe=Nein, so I have to use query or filter to exclude those

        mtype = "Object"
        saved_query = 12345
        [Filter]
            action = "filter"
            ftype = "repeatableGroup.dataField"
            field = "ObjPublicationGrp.Freigabe"
            match = "not equals"
            value = "Nein"
        [Freigabe1]
            action = "new_or_write"
            ftype = "repeatableGroup.dataField"
            field = "ObjPublicationGrp.Freigabe" 
            value = "Ja"
        [Freigabe2]
            action = "new_or_write"
            field = "repeatableGroup:ObjPublicationGrp.dataField:Typ", 
            value = "Freigabe für SMB-Digital"
        [Freigabe3]
            action = "new_or_write"
            field = "ObjPublicationGrp.Bemerkung", 
            value = "Freigegeben durch MDVOS"
        """

    # should probably not be here
    def _toString(self, node) -> None:
        return etree.tostring(node, pretty_print=True, encoding="unicode")
