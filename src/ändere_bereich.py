import argparse
from copy import deepcopy  # for lxml
from lxml import etree  # t y p e : i g n o r e
from mpapi.client import MpApi
from mpapi.constants import get_credentials, NSMAP
from mpapi.search import Search
from mpapi.module import Module
from pathlib import Path

"""
This is a simple search/replace where we call only low-level modules. 
"""


def main(cache: bool = False, limit: int = -1) -> None:
    # configuration
    old_unit = "EMAllgemein"
    new_unit = "EMAfrika1"  # AKuArchivSSOZ?
    grp_ID = 778398
    mtype = "Object"  # or Multimedia

    # do a query
    m = _query_ria(
        cache=cache, grp_ID=grp_ID, limit=limit, mtype=mtype, old_unit=old_unit
    )

    # change online records
    replace2(data=m, limit=limit, mtype=mtype, new_unit=new_unit)
    print(">>Success")


def replace1(*, client: MpApi, data: Module, limit: int) -> None:
    """
    OBSOLETE. Stays here for future reference
    Apparently, I cant change systemField using updateField endpoint. Not the first time I
    try this.
    """
    print(">>Enter replace1 using endpoint updateField")
    mtype = "Object"
    itemL = data.xpath(
        f"/m:application/m:modules/m:module[@name = '{mtype}']/m:moduleItem"
    )
    for idx, itemN in enumerate(itemL, start=1):
        ID = int(itemN.xpath("@id", namespaces=NSMAP)[0])
        orgUnit = itemN.xpath(
            "m:systemField[@name = '__orgUnit']/m:value/text()", namespaces=NSMAP
        )[0]
        print(f"{ID}")
        m = Module()
        mm = m.module(name=mtype)
        item = m.moduleItem(parent=mm, ID=ID)
        m.systemField(
            parent=item, dataType="Varchar", name="__orgUnit", value="EMAfrika1"
        )
        m.validate()
        xml = m.toString()
        print(xml)
        client.updateField(module=mtype, id=ID, dataField="__orgUnit", xml=xml)

        if idx == limit:
            print(">>Limit reached")
            break


def replace2(*, data: Module, limit: int, mtype: str, new_unit: str) -> None:
    """
    Let's try to change the whole record.
    """
    print(">>Enter replace2 using endpoint updateItem")
    user, pw, baseURL = get_credentials()
    print(f">>Logging in as '{user}'")
    client = MpApi(baseURL=baseURL, user=user, pw=pw)
    itemL = data.xpath(
        f"/m:application/m:modules/m:module[@name = '{mtype}']/m:moduleItem"
    )
    for idx, itemN in enumerate(itemL, start=1):
        itemN = deepcopy(itemN) # so that uploadform doesn't change original
        ID = int(itemN.xpath("@id", namespaces=NSMAP)[0])
        print(f">>{ID} changing orgUnit to '{new_unit}'")
        orgUnitN = itemN.xpath(
            "m:systemField[@name = '__orgUnit']/m:value", namespaces=NSMAP
        )[0]
        orgUnitN.text = new_unit

        m = Module()
        mm = m.module(name=mtype)
        mm.append(itemN)
        m.uploadForm()
        # print(m.toString())
        m.validate()
        client.updateItem2(mtype=mtype, ID=ID, data=m)

        if idx == limit:
            print(">>Limit reached")
            break


def search(*, ID: int, limit: int = -1, old_unit: str, mtype: str = "Object") -> Search:
    query = Search(module=mtype, limit=limit)
    query.AND()
    query.addCriterion(
        operator="equalsField",  # notEqualsTerm
        field="__orgUnit",  # __orgUnit is not allowed in Zetcom's own search.xsd
        value=old_unit,
    )
    match mtype:
        case "Object":
            query.addCriterion(
                operator="equalsField",
                field="ObjObjectGroupsRef.__id",  # ObjCurrentLocationVoc
                value=str(ID),
            )
        case "Multimedia":
            query.addCriterion(
                operator="equalsField",
                field="MulObjectRef.ObjObjectGroupsRef.__id",
                value=str(ID),
            )
        case _:
            raise SyntaxError(f"Unknown mtype: {mtype}")

    # if we update the whole record, we need the whole record
    # query.addField(field="__orgUnit")

    query_fn = "debug.query.xml"
    print(f"Writing query to {query_fn}")
    query.toFile(path=query_fn)
    query.validate(mode="search")
    return query


#
# more private
#


def _query_ria(
    *, cache: bool, grp_ID: int, limit: int, old_unit: str, mtype: str
) -> Module:
    results_fn = Path("debug.results.xml")
    if cache:
        if not results_fn.exists():
            raise TypeError(
                "You requested to use a file cache, but file does not exist"
            )
        print(">>Using cached search results")
        m = Module(file=results_fn)
    else:
        print(">>Getting fresh results")
        user, pw, baseURL = get_credentials()
        print(f">>Logging in as '{user}'")
        c = MpApi(baseURL=baseURL, user=user, pw=pw)
        q = search(
            ID=grp_ID, limit=limit, old_unit=old_unit, mtype=mtype
        )  # your input here
        m = c.search2(query=q)
        print("Writing query results to {results_fn}")
        m.toFile(path=results_fn)  # delete manually
    return m

#
#
#

if __name__ == "__main__":
    # we currently dont have -a act flag
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l",
        "--limit",
        help="Stop the execution after x number of items",
        type=int,
        default=-1,
    )
    parser.add_argument(
        "-c", "--cache", help="Use cached response", action="store_true"
    )
    args = parser.parse_args()
    main(cache=args.cache, limit=args.limit)
