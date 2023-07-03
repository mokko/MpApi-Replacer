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
    # only run sometimes
    if not Path("group-487399.xml").exists:
        user, pw, baseURL = get_credentials()
        r = Replace2(baseURL=baseURL, conf_fn="conf_group.toml", pw=pw, user=user)
        dataM = r.search()
        assert r
    
def test_filter():
    r = Replace2(baseURL="fake", conf_fn="conf.toml", cache=True, pw="fake", user="fake")
    r.conf["FILTER"] = []
    filterL = r.conf["FILTER"]

    filterL.append({
        "field":"ObjPublicationGrp.PublicationVoc", 
        "type": "repeatableGroup.vocabularyReference", 
        "match": "!=",
        "value": 4491690 # Nein
        })
    filterL.append({
        "field":"__id", 
        "type": "systemField", 
        "match": "=",
        "value": 1838348 # ID
        })
    filterL.append({
        "field":"ObjTechnicalTermClb", 
        "type": "dataField", 
        "match": "=",
        "value": "Schallplatte" 
        })
    filterL.append({
        "field":"ObjDateVrt", # Herstellungsdatum
        "type": "virtualField", 
        "match": "=",
        "value": "1978" 
        })
    dataM = r.search()
    assert len(dataM) == 1
