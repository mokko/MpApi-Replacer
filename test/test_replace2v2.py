"""
Test import
"""

from MpApi.Replace.replace2 import Replace2
from mpapi.constants import get_credentials
from mpapi.module import Module
from pathlib import Path


def test_constructor():
    r = Replace2(baseURL="fake", conf_fn="conf.toml", pw="fake", user="fake")


def test_input_group():
    if not Path("group-487399.xml").exists:
        r = Replace2(
            baseURL="fake",
            conf_fn="conf_group.toml",
            cache=True,
            pw="fake",
            user="fake",
        )
    else:  # only run with http request when you have to
        user, pw, baseURL = get_credentials()
        r = Replace2(baseURL=baseURL, conf_fn="conf_group.toml", pw=pw, user=user)
    dataM = r.search()
    assert r


def test_filter():
    r = Replace2(
        baseURL="fake", conf_fn="conf.toml", cache=True, pw="fake", user="fake"
    )
    r.conf["FILTER"] = []
    filterL = r.conf["FILTER"]

    filterL.append(
        {
            "field": "ObjPublicationGrp.PublicationVoc",
            "type": "repeatableGroup.vocabularyReference",
            "match": "!=",
            "value": 4491690,  # Nein
        }
    )
    filterL.append(
        {"field": "__id", "type": "systemField", "match": "=", "value": 1838348}  # ID
    )
    filterL.append(
        {
            "field": "ObjTechnicalTermClb",
            "type": "dataField",
            "match": "=",
            "value": "Schallplatte",
        }
    )
    filterL.append(
        {
            "field": "ObjDateVrt",  # Herstellungsdatum
            "type": "virtualField",
            "match": "=",
            "value": "1978",
        }
    )
    filterL.append(
        {
            "field": "ObjOrgGroupVoc",
            "type": "vocabularyReference",
            "match": "=",
            "value": "1632800",  # EM-Medienarchiv
        }
    )
    filterL.append(
        {
            "field": "ObjObjectNumberGrp.InventarNrSTxt",
            "type": "repeatableGroup.dataField",
            "match": "=",
            "value": "VII LP 3869",  # IdentNr
        }
    )
    filterL.append(
        {
            "field": "ObjObjectNumberGrp.NumberWithoutSpecialCharactersVrt",
            "type": "repeatableGroup.virtualField",
            "match": "=",
            "value": "VIILP3869",  # IdentNr sort
        }
    )
    filterL.append(
        {
            "field": "ObjObjectNumberGrp.DenominationVoc",
            "type": "repeatableGroup.vocabularyReference",
            "match": "=",
            "value": "2737051",  # Ident. Nr.
        }
    )
    filterL.append(
        {
            "field": "ObjObjectNumberGrp.InvNumberSchemeRef",
            "type": "repeatableGroup.moduleReference",
            "match": "=",
            "value": "152",  # Ident. Nr.
        }
    )
    dataM = r.search()
    assert len(dataM) == 1


def test_field_exists():
    r = Replace2(
        baseURL="fake", conf_fn="conf.toml", cache=True, pw="fake", user="fake"
    )
    dataM = r.search()
    cmd = {"field": "__id", "type": "systemField"}
    ret = r._field_exists(data=dataM, cmd=cmd, ID=1838348)
    assert ret

    cmd = {"field": "doesNotExist", "type": "systemField"}
    ret = r._field_exists(data=dataM, cmd=cmd, ID=1838348)
    assert ret is False

    cmd = {"field": "ObjPublicationStatusVoc", "type": "vocabularyReference"}
    ret = r._field_exists(data=dataM, cmd=cmd, ID=1838348)
    assert ret

    cmd = {
        "field": "ObjObjectNumberGrp.NumberWithoutSpecialCharactersVrt",
        "type": "repeatableGroup.virtualField",
    }
    ret = r._field_exists(data=dataM, cmd=cmd, ID=1838348)
    assert ret

    cmd = {
        "field": "ObjObjectNumberGrp.DoesNotExist",
        "type": "repeatableGroup.virtualField",
    }
    ret = r._field_exists(data=dataM, cmd=cmd, ID=1838348)
    assert ret is False
    # raise TypeError


def test_replace():
    user, pw, baseURL = get_credentials()
    r = Replace2(baseURL=baseURL, conf_fn="conf.toml", cache=True, pw=pw, user=user)
    # newL = r.conf["NEW"]
    # newL.append({"field": "DoesNotExist", "type": "dataField", "value": "random value"})
    # newL.append(
    # {"field": "DoesNotExist", "type": "systemField", "value": "random value"}
    # )
    # newL.append(
    # {"field": "DoesNotExist", "type": "virtualField", "value": "random value"}
    # )
    dataM = r.search()
    print("REPLACE")
    r.replace(search_results=dataM)
