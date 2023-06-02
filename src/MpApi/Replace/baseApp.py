"""

Code that is reusable over multiple replacer apps

"""

from mpapi.client import MpApi
from mpapi.module import Module

try:
    import tomllib  # Python v3.11
except ModuleNotFoundError:
    import tomli as tomllib  # < Python v3.11


# user-facing field names: no space, no period, no slash
RIA_data = {
    "Asset": {},
    "Multimedia": {
        "Anlass": "vocabularyReference:MulShootingReasonVoc",
        "Bereich": {
            "systemField:__orgUnit": {
                "EMAfrika1": "EM-Afrika",
                "EMAllgemein": "EM-Allgemein",
                "EMAmArchaologie": "EM-Am Archaologie",
                "EMAmEthnologie": "EM-Am Ethnologie",
                "EMMedienarchiv": "EM-Medienarchiv",
                "EMMusikethnologie": "EM-Musikethnologie",
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
        "Funktion": "vocabularyReference:MulCategoryVoc",
        "InhAns": "dateField:MulSubjectTxt",
        "MatTech": "vocabularyReference:MulMatTechVoc",
        "Status": "vocabularyReference:MulStatusVoc",
        "TypDetails": "dataField:MulTypeTxt",
        "Typ": "vocabularyReference:MulTypeVoc",
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
        print(f"Logged in as {user}")

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

    def _init_conf(self, *, conf_fn: str) -> dict:
        with open(conf_fn, "rb") as f:
            conf = tomllib.load(f)

        for required in ["module", "savedQuery", "replace"]:
            if not required in conf:
                raise Exception(
                    f"ERROR: Required configuration value '{required}' missing!"
                )
        return conf

    def _rewrite_conf(self, conf) -> dict:
        """
        Sanitizes a bit and rewrites external with internal RIA values
        """
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

            f_in = list(RIA_data[mtype][f_ex].keys())[0]
            action2["field"] = f_in
            action2["f_ex"] = f_ex
            action2["s_ex"] = s_ex
            action2["r_ex"] = r_ex

            # print(f"f_in: {f_in}")
            try:
                action2["search"] = RIA_data[mtype][f_ex][f_in][s_ex]
            except KeyError:
                raise SyntaxError(
                    f"ERROR: external search value '{s_ex}' not in {mtype}: {f_ex}"
                )
            try:
                action2["replace"] = RIA_data[mtype][f_ex][f_in][r_ex]
            except:
                raise SyntaxError(
                    f"ERROR: external replace value '{r_ex}' not in {mtype}: {f_ex}"
                )
            new["replace"].append(action2)
        return new
