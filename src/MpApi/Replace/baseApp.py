"""

Code that is reusable over multiple replacer apps

"""

from lxml import etree
from mpapi.client import MpApi
from mpapi.module import Module
import pprint

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # < Python v3.11

# why does eq and ne not work? Is that not valid xpath?
# todo: contains; contains is not meaningful for IDs
allowed_match = ("=", "!=")
allowed_types = (
    "composite",
    "dataField",
    "moduleReference",
    "repeatableGroup",
    "systemField",
    "virtualField",
    "vocabularyReference",
)
# no filter for composite written yet


class ConfigError(Exception):
    pass


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
        conf = self._init_conf(conf_fn=conf_fn)
        self.conf = self._parse_conf(conf)
        pprint.pprint(self.conf)
        print(f"Logged in as {user}")

    def replace(self, *, search_results: Module) -> None:
        """
        Loops through all items in the search results and call the actions for the
        current job (i.e. in the toml config file).
        """

        mtype = self.conf["INPUT"]["mtype"]
        IDs = search_results.xpath(
            f"/m:application/m:modules/m:module[@name='{mtype}']/m:moduleItem/@id"
        )

        # to avoid deep copy, so we loop thru one big document with many items
        for ID in IDs:
            self._per_item(doc=search_results, ID=ID)

    def search(self) -> Module:
        """
        Get the initial input from RIA, then process the filters to weed out some
        more records.
        """

        m = self._get_input()
        m = self._process_filters(data=m)
        m.toFile(path="debug.afterFilter.xml")
        return m

    #
    # private
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

    def _each_filter(self, *, Filter: dict, data: Module) -> Module:
        mtype = self.conf["INPUT"]["mtype"]
        types = Filter["type"].split(".")
        fields = Filter["field"].split(".")
        match = Filter["match"]
        value = Filter["value"]

        if match not in allowed_match:
            raise ConfigError(f"ERROR: Unknown match {match}")

        for atype in types:
            if atype not in allowed_types:
                raise ConfigError(f"ERROR: Unknown field type '{atype}'")

        xpath = f"/m:application/m:modules/m:module[@name='{mtype}']/m:moduleItem"
        xpath += "["

        for c in range(len(types)):
            atype = types[c]
            afield = fields[c]
            if atype == "repeatableGroup":
                xpath += f"m:{atype}[@name='{afield}']"
                xpath += "/m:repeatableGroupItem"
            elif (
                atype == "dataField"
                or atype == "systemField"
                or atype == "virtualField"
            ):
                xpath += f"m:{atype}[@name='{afield}']"
            elif atype == "moduleReference":
                xpath += f"m:{atype}[@name='{afield}']"

            elif atype == "vocabularyReference":
                xpath += f"m:{atype}[@name='{afield}']"
            else:
                raise ConfigError(f"filter type '{atype }' not yet implemented")

            if c < (len(types) - 1):  # not last one
                xpath += "/"

        if types[-1] == "vocabularyReference":
            xpath += f"/m:vocabularyReferenceItem[@id {match} '{value}']"
        elif types[-1] == "moduleReference":
            xpath += f"/m:moduleReferenceItem[@moduleItemId {match} '{value}']"
        elif (
            types[-1] == "dataField"
            or types[-1] == "systemField"
            or types[-1] == "virtualField"
        ):
            xpath += f"[m:value {match} '{value}']"
        else:
            raise ConfigError(f"filter type '{atype }' not yet implemented")

        xpath += "]"

        print(xpath)
        resultL = data.xpath(xpath)
        # wrap
        new = Module()
        moduleN = new.module(name=mtype)
        for resultN in resultL:
            moduleN.append(resultN)
        # print (resultL)
        print(len(new))
        return new

    def _field2xml(self, node):
        """
        This is a version of wrap for fields. Perhaps I will rename it in the future.
        """
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

    def _get_input(self) -> Module:
        INPUT = self.conf["INPUT"]
        print(INPUT)
        ID = None
        search_type = None
        try:
            self.conf["INPUT"]["saved_query"]
        except:
            pass
        else:
            ID = int(self.conf["INPUT"]["saved_query"])
            search_type = "savedQuery"
        try:
            self.conf["INPUT"]["group"]
        except:
            pass
        else:
            ID = int(self.conf["INPUT"]["group"])
            search_type = "group"
        if ID is None:
            raise ConfigError(f"ERROR: Unknown search type '{search_type}'")

        print(f"{search_type} {ID}")
        cache_fn = f"{search_type}-{ID}.xml"

        if self.cache:
            print(f"* Getting search results from file cache '{cache_fn}'")
            m = Module(file=cache_fn)
        else:
            m = self._search(search_type=search_type, ID=ID, cache_fn=cache_fn)

        print(f"* results {len(m)}")
        return m

    def _init_conf(self, *, conf_fn: str) -> dict:
        with open(conf_fn, "rb") as f:
            return tomllib.load(f)

    def _parse_conf(self, conf: dict) -> dict:
        """
        config parser for version 2 config files. This only copies allowed keywords and
        doesn't do any significant testing on allowed keys and values on lower levels.
        """

        new_conf = {}

        try:
            conf["INPUT"]
        except:
            raise ConfigError("Required config section 'INPUT' missing")
        else:
            new_conf["INPUT"] = conf["INPUT"]

        for optional in (
            "ADD",
            "ADD_OR_NEW",
            "FILTER",
            "NEW",
            "NEW_OR_WRITE",
            "SUB",
            "WRITE",
        ):
            try:
                conf[optional]
            except:
                pass
            else:
                new_conf[optional] = conf[optional]

        for cmd in new_conf:
            if cmd == "INPUT":
                try:
                    new_conf["INPUT"]["mtype"]
                except:
                    raise ConfigError("ERROR: Input needs mtype")
            else:
                cmdL = new_conf[cmd]
                for acmd in cmdL:
                    for key in ("field", "type", "value"):
                        try:
                            acmd[key]
                        except:
                            raise ConfigError(f"ERROR: {cmd} needs {key}")
                    typeL = acmd["type"].split(".")
                    fieldL = acmd["field"].split(".")
                    if len(typeL) > 2:
                        # repeatableGroup.dataField -> OK
                        # repeatableGroup.repeatableGroup.dataField -> not OK
                        raise ConfigError(
                            "ERROR: Currently we're only allowing first "
                            + f"order subfields: '{acmd['type']}'"
                        )
                    if len(typeL) != len(fieldL):
                        raise ConfigError(
                            "ERROR: Type and field need same length: "
                            + f"'{acmd['type']}'"
                        )

                    for atype in typeL:
                        if atype not in allowed_types:
                            raise ConfigError(f"ERROR: '{atype}' not allowed")
                    # check ridiculous combinations like dataField.dataField
                    atype = acmd["type"]  # whole
                    if atype.startswith("dataField"):
                        if len(atype) > 8:
                            raise ConfigError(f"ERROR: Type not allowed: {atype}")
                    elif atype.startswith("systemField"):
                        if len(atype) > 11:
                            raise ConfigError(f"ERROR: Type not allowed: {atype}")
                    elif atype.startswith("virtualField"):
                        if len(atype) > 11:
                            raise ConfigError(f"ERROR: Type not allowed: {atype}")
        print("Config file valid")
        return new_conf

    def _process_filters(self, data: Module) -> Module:

        try:
            self.conf["FILTER"]
        except:
            return data

        if len(data) == 0:
            raise ConfigError("ERROR: Search returns 0 results")

        for each in self.conf["FILTER"]:
            data = self._each_filter(Filter=each, data=data)
        return data

    def _search(self, *, ID: int, cache_fn: str, search_type: str) -> Module:
        mtype = self.conf["INPUT"]["mtype"]
        print(f"* Getting {mtype} from {search_type} {ID}")
        if search_type == "savedQuery":
            m = self.ria.runSavedQuery3(ID=ID, Type=mtype)
        elif search_type == "group":
            m = self.ria.getItem2(ID=ID, mtype=mtype)
        # todo for exhibit

        print(f"* Writing search results to {cache_fn}")
        m.toFile(path=cache_fn)  # overwrites old files
        return m

    # should probably not be here
    def _toString(self, node) -> None:
        return etree.tostring(node, pretty_print=True, encoding="unicode")


if __name__ == "__main__":
    pass
