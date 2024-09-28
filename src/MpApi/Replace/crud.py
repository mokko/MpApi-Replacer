"""

In order to make it easier to change lxml documents, should we offer a

crud interface to access fields in the lxml documents?

create: create a new field in doc; raise if field already exists
read: get an existing field or return None if field doesn't exist
update: change an existing field to new value; if old and new value are the same,
    treat that as success
delete: delete a field
create_or_update: create a field if it doesn't exist yet and set it to new value or
    update it to new value if it already exists

Should this become part of Module or record?

    m = Module(file="path/to/zml")
    r = record(file="path/to/zml")

    context="m:application/m:modules/module[@name='Object']/m:moduleItem[@id = 'ID']/m:repeatableGroup[@name='ObjPublicationGrp']"
    m.create(context=context, ttype="dataField", field="NotesClb", value="some text describing the Freigabe")


    r.create("m:repeatableGroup[@name='ObjPublicationGrp']", "m:dataField[@name='NotesClb']", "Beispiel")
    str = r.read("m:repeatableGroup[@name='ObjPublicationGrp']", "m:dataField[@name='NotesClb']")
    r.update("m:repeatableGroup[@name='ObjPublicationGrp']", "m:dataField[@name='NotesClb']", "Beispiel")
    r.delete("m:repeatableGroup[@name='ObjPublicationGrp']", "m:dataField[@name='NotesClb']")
    r.create_or_update("m:repeatableGroup[@name='ObjPublicationGrp']", "m:dataField[@name='NotesClb']", "Beispiel")

"""
