"""
Combines Tabula's mapping and Timetable reports to form single room mapping

Update central room info periodically from https://warwick.ac.uk/services/its/servicessupport/av/lecturerooms/roominformation/room-data.js
  Convert from js to json, e.g. with https://www.convertsimple.com/convert-javascript-to-json/
Update tabula mapping `tabula-sciencianame.txt"` from Tabula src code: common/src/main/scala/uk/ac/warwick/tabula/services/timetables/ScientiaCentrallyManagedRooms.scala
  Chop off ends and comments, then can regex convert `"(.+)" -> MapLocation\("(.+)", "(\d+)", Some\("(.+)"\)\),` to `$2 | $1`
Update scientia mapping `scientianame-url.txt` from http://go.warwick.ac.uk/timetablereports > Locations > Inspect "Select Room(s)" menu, and copy out
  Again also regex convert
"""


def read_mapping(filename):
    with open(str(filename)) as f:
        l = [l.split(" | ") for l in f.readlines()]
        return {x[0].strip(): x[1].strip() for x in l if len(x) > 1}


tabtonames = read_mapping("tabula-sciencianame.txt")
nametourl = read_mapping("scientianame-url.txt")


# Custom mappings
custom_tabtoname = {
    "MS_A1.01": "A1.01 (Zeeman)",
    "FAC.SS_S2.77": "FD_S2.77",
    "H1.48": "PS_H1.48",
    "C1.11 / C1.13 / C1.1": "c1.11/15",
    "MS.B3.03": "B3.03 (Zeeman)",
    "Language Centre Training Room": "LN_H0.83",
    "A0.39": "A0.39 (Gibbet Hill)",
    # A whole bunch of Hxxx are under LL not LN
    "H0.78": "LN_H0.78",
    "H0.67": "LN_H0.67",
    "H0.82": "LN_H0.82",
    "H0.79": "LN_H0.79",
    "H0.72": "LN_H0.72",
}

print("Missing Conversions")
mapping = {}
for tab in tabtonames:
    if tab in custom_tabtoname:
        name = custom_tabtoname[tab]
    else:
        name = tabtonames.get(tab)
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
