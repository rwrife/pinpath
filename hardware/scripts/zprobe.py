import pcbnew
from collections import Counter

b = pcbnew.LoadBoard(__import__("sys").argv[1])
zones = list(b.Zones())
print("zones:", len(zones), Counter(z.GetNetname() for z in zones))
print("filled mm2:", [round(z.GetFilledArea() / 1e6, 1) for z in zones][:14])
nds = b.GetDesignSettings()
try:
    names = [str(n) for n in nds.GetNetclasses()]
    print("netclasses:", names)
    for nm in names:
        nc = nds.GetNetClassByName(nm)
        print(" ", nm, "clearance", nc.GetClearance() / 1e6, "width", nc.GetTrackWidth() / 1e6)
except Exception as e:
    print("netclass probe err:", e)
w = Counter(round(t.GetWidth() / 1e6, 3) for t in b.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T)
print("width hist:", dict(w))
for ref in ("U2", "U6", "D34", "R77", "TP8", "U8", "U4"):
    fp = b.FindFootprintByReference(ref)
    if fp:
        pads = [(p.GetPadName(), round(p.GetPosition().x / 1e6, 2), round(p.GetPosition().y / 1e6, 2), p.GetNetname()) for p in fp.Pads()]
        print(ref, fp.GetFPID().GetLibItemName(), len(pads), "pads", pads[:3])
