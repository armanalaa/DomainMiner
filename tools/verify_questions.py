examples = [
    """tariffe = {"base": 12, "extra": 5, "base": 15}
print(len(tariffe), tariffe["base"])""",
    """righe = {"prima": ["A", "B"], "seconda": ["C"]}
righe["prima"].append("D")
print(righe["prima"], len(righe))""",
    """inizio = 4
scheda = {
    "codice": "P" + str(inizio * 3),
    "intervallo": {"min": inizio - 1, "max": inizio + 5},
    "ampiezza": (inizio + 5) - (inizio - 1)
}
inizio = 10
print(scheda["codice"], scheda["intervallo"]["max"], scheda["ampiezza"])""",
    """a = {"x": [1, 2], "y": 3}
b = {"y": 3, "x": [2, 1]}
print(a == b)
a["x"].sort(reverse=True)
print(a == b)""",
    """agenda = {}
agenda["lun"] = ["analisi"]
agenda["mar"] = ["reti"]
agenda["lun"] = agenda["lun"] + ["python"]
print(agenda["lun"][1], "ven" in agenda, len(agenda))""",
]

for i, code in enumerate(examples, 1):
    print(f"--- Q{i} ---")
    exec(code)
