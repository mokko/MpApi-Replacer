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
   
    
"""
