"""
Manually run. Combines Tabula's mapping and Timetable reports to form single room mapping
These data sources need manually fetching, so combining them is a one time thing.

Data update instructions:
    Update central room info `central-room-data.json` periodically from https://warwick.ac.uk/services/its/servicessupport/av/lecturerooms/roominformation/room-data.js
      Convert from js to json, e.g. with https://www.convertsimple.com/convert-javascript-to-json/
    Update tabula mapping `tabula-sciencianame.txt` from Tabula src code: common/src/main/scala/uk/ac/warwick/tabula/services/timetables/ScientiaCentrallyManagedRooms.scala
      Chop off ends and comments, then can regex convert `"(.+)" -> MapLocation\("(.+)", "(\d+)", Some\("(.+)"\)\),` to `$2 | $1`
    Update scientia mapping `scientianame-url.txt` from http://go.warwick.ac.uk/timetablereports > Locations > Inspect "Select Room(s)" menu, and copy out
      Again also regex convert

Files:
    Warwick provides maps: tabula (~campus map) to scientia (timetable management), and scientia to room booking url key.
    These are in `tabula-sciencianame.txt"` and `scientianame-url.txt`.
    Custom room names on the tabula to sciencia step are in `custom-tabstoname.txt`
    Aliases for rooms which don't appear in the map autocomplete are in `customsearch.txt` (e.g. CS teaching room <-> MB0.01)
    `room_to_surl.txt` is the final resulting mapping

    `central-room-data.json` holds data for the list of centrally timetabled rooms (rooms that are bookable through uni timetabling, and a ITS AV page exists for)
"""


def read_mapping(filename):
    with open(str(filename)) as f:
        l = [l.split(" | ") for l in f.readlines()]
        return {x[0].strip(): x[1].strip() for x in l if len(x) > 1}


tabtonames = read_mapping("tabula-sciencianame.txt")
nametourl = read_mapping("scientianame-url.txt")

custom_names = read_mapping("customsearch.txt")
custom_tabtoname = read_mapping("custom-tabtosname.txt")


print("Missing Conversions")
mapping = {}
for tab, n in (tabtonames | custom_names).items():
    if tab in custom_tabtoname:
        name = custom_tabtoname[tab]
    else:
        name = n
    url = nametourl.get(name)
    if url is None:
        url = nametourl.get(tab)
    if url is None:
        print(tab, "|", name, "|", url)
    else:
        mapping[tab] = url

for name in nametourl:
    if name not in mapping.keys() and name not in mapping.values():
        v = nametourl[name]
        mapping[name] = mapping[name] = v


with open("room_to_surl.txt", "w") as room_to_surl:
    for k, v in mapping.items():
        room_to_surl.write(f"{k} | {v}\n")
