import argparse
from copy import deepcopy  # for lxml
from lxml import etree  # t y p e : i g n o r e
from mpapi.client import MpApi
from mpapi.constants import get_credentials, NSMAP
from mpapi.search import Search
from mpapi.module import Module
from pathlib import Path

"""
This is a simple search/replace where we call only low-level modules
"""


def main(limit: int = -1) -> None:
    # initialize
    user, pw, baseURL = get_credentials()
    print(f">>Logging in as '{user}'")
    c = MpApi(baseURL=baseURL, user=user, pw=pw)

    # do a query
    results_fn = Path("debug.results.xml")
    if results_fn.exists():
        print(">>Using cached search results")
        m = Module(file=results_fn)
    else:
        print(">>Getting full fresh results")
        q = search(Id=778398, limit=limit)  # your input here
        m = c.search2(query=q)
        print("Writing query results to {results_fn}")
        m.toFile(path=results_fn)  # delete manually if required

    # change online records todo
    replace2(client=c, data=m, limit=limit)


def replace1(*, client: MpApi, data: Module, limit: int) -> None:
    """
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
        print(f"{ID} {orgUnit}")
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


def replace2(*, client: MpApi, data: Module, limit: int) -> None:
    """
    Let's try to change the whole record.
    """
    print(">>Enter replace2 using endpoint updateItem")
    mtype = "Object"
    itemL = data.xpath(
        f"/m:application/m:modules/m:module[@name = '{mtype}']/m:moduleItem"
    )
    for idx, itemN in enumerate(itemL, start=1):
        itemN = deepcopy(itemN)
        ID = int(itemN.xpath("@id", namespaces=NSMAP)[0])
        print(f">>{ID} changing orgUnit to EMAfrika1")
        orgUnitN = itemN.xpath(
            "m:systemField[@name = '__orgUnit']/m:value", namespaces=NSMAP
        )[0]
        orgUnitN.text = "EMAfrika1"

        m = Module()
        mm = m.module(name=mtype)
        mm.append(itemN)
        m.uploadForm()
        print(m.toString())
        m.validate()
        client.updateItem2(mtype=mtype, ID=ID, data=m)

        print()
        if idx == limit:
            print(">>Limit reached")
            break


def search(*, Id: int, limit: int = -1) -> Search:
    query = Search(module="Object", limit=limit)
    query.AND()
    query.addCriterion(
        operator="equalsField",  # notEqualsTerm
        field="__orgUnit",  # __orgUnit is not allowed in Zetcom's own search.xsd
        value="EMAllgemein",
    )
    query.addCriterion(
        operator="equalsField",
        field="ObjObjectGroupsRef.__id",  # ObjCurrentLocationVoc
        value=str(Id),  # using voc id
    )
    # if we update the whole record, we need the whole record
    # query.addField(field="__orgUnit")

    # query.addCriterion(
    # operator="equalsField",
    # field="MulObjectRef.ObjObjectGroupsRef.__id",
    # value="31393",  # Gruppe
    # )
    query_fn = "query.xml"
    print(f"Writing query to {query_fn}")
    query.toFile(path=query_fn)
    query.validate(mode="search")
    return query


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l",
        "--limit",
        help="Stop the execution after x number of items",
        type=int,
        default=-1,
    )
    args = parser.parse_args()
    main(limit=args.limit)
