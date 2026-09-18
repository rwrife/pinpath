import re
txt = open("pinpath.kicad_sch").read()
for m in re.finditer(r"\(symbol \(lib_id", txt):
    seg = txt[m.start():m.start() + 4000]
    ref = re.search(r'"Reference" "([A-Z]+\d+)"', seg)
    fp = re.search(r'"Footprint" "([^"]*)"', seg)
    if ref and fp and not fp.group(1):
        print(ref.group(1), repr(fp.group(1)))
