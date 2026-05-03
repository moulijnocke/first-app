from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import date, datetime, timedelta
import ollama
import re

app = Flask(__name__)
DATA_FILE = "data.json"

PROFIEL = {
    "kcal_doel": 2500,
    "eiwit_doel": 180,
    "naam": "Ocke"
}

VAST_ONTBIJT = {
    "naam": "Vast ontbijt (yoghurt, crusli, creatine, banaan)",
    "kcal": 550,
    "eiwit": 25
}

# Vaste voedingswaarden voor snelknoppen
VOEDINGSWAARDEN = {
    "Komkommer": {"kcal": 15, "eiwit": 1},
    "Kipfilet": {"kcal": 165, "eiwit": 31},
    "Ei": {"kcal": 78, "eiwit": 6},
    "Philadelphia": {"kcal": 120, "eiwit": 3},
    "Brood": {"kcal": 80, "eiwit": 3},
    "Kaas": {"kcal": 110, "eiwit": 7},
    "Banaan": {"kcal": 89, "eiwit": 1},
    "Druif": {"kcal": 62, "eiwit": 1},
    "Kiwi": {"kcal": 42, "eiwit": 1},
    "Yoghurt": {"kcal": 100, "eiwit": 10},
    "Crusli": {"kcal": 180, "eiwit": 4},
    "Koffie": {"kcal": 5, "eiwit": 0},
    "Koekje": {"kcal": 80, "eiwit": 1}
}

CATEGORIEEN = {
    "Groente & fruit": ["komkommer", "tomaat", "sla", "spinazie", "broccoli", "wortel", "paprika", "ui", "knoflook", "avocado", "banaan", "appel", "peer", "druif", "kiwi", "aardbei", "mango", "citroen"],
    "Vlees & vis": ["kip", "kipfilet", "gehakt", "biefstuk", "zalm", "tonijn", "ham", "spek", "worst"],
    "Zuivel & eieren": ["ei", "melk", "yoghurt", "kwark", "kaas", "philadelphia", "boter", "room", "skyr"],
    "Granen & brood": ["brood", "pasta", "rijst", "havermout", "crusli", "crackers", "wraps", "tortilla"],
    "Blikken & potten": ["tomatenblokjes", "kikkererwten", "bonen", "mais", "pindakaas", "jam", "olijven"],
    "Snacks": ["koekje", "chips", "noten", "reep", "protein bar", "rijstwafels"],
    "Dranken": ["koffie", "thee", "sap", "frisdrank", "water", "sportdrank", "proteine shake"],
    "Verzorging": ["shampoo", "deo", "tandpasta", "gel", "scheerschuim", "zeep", "wasverzachter"],
    "Schoonmaak": ["afwasmiddel", "allesreiniger", "wc blokjes", "vuilniszakken", "doekjes"],
}

def bepaal_categorie(naam):
    naam_lower = naam.lower()
    for categorie, keywords in CATEGORIEEN.items():
        if any(kw in naam_lower for kw in keywords):
            return categorie
    return "Overig"

def laad_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"voorraad": [], "boodschappenlijst": [], "dagboek": {}, "favorieten": [], "water": {}, "notities": {}}

def sla_op(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def vandaag():
    return str(date.today())

def bereken_dagboek(dagboek_vandaag):
    kcal = VAST_ONTBIJT["kcal"]
    eiwit = VAST_ONTBIJT["eiwit"]
    for item in dagboek_vandaag:
        kcal += item.get("kcal", 0)
        eiwit += item.get("eiwit", 0)
    return kcal, eiwit

def bereken_streak(dagboek):
    streak = 0
    dag = date.today()
    while True:
        dag_str = str(dag)
        if dag_str in dagboek:
            _, eiwit = bereken_dagboek(dagboek[dag_str])
            eiwit += VAST_ONTBIJT["eiwit"]
            if eiwit >= PROFIEL["eiwit_doel"]:
                streak += 1
                dag -= timedelta(days=1)
            else:
                break
        else:
            break
    return streak

def bereken_week(dagboek):
    week = []
    for i in range(6, -1, -1):
        dag = date.today() - timedelta(days=i)
        dag_str = str(dag)
        dag_data = dagboek.get(dag_str, [])
        kcal, _ = bereken_dagboek(dag_data)
        week.append({
            "dag": dag.strftime("%a"),
            "kcal": kcal,
            "doel": PROFIEL["kcal_doel"]
        })
    return week

@app.route("/")
def index():
    data = laad_data()
    dag = vandaag()
    dagboek_vandaag = data["dagboek"].get(dag, [])
    kcal_gehad, eiwit_gehad = bereken_dagboek(dagboek_vandaag)
    kcal_nog = max(0, PROFIEL["kcal_doel"] - kcal_gehad)
    eiwit_nog = max(0, PROFIEL["eiwit_doel"] - eiwit_gehad)
    streak = bereken_streak(data.get("dagboek", {}))
    week = bereken_week(data.get("dagboek", {}))
    water_vandaag = data.get("water", {}).get(dag, 0)
    notitie_vandaag = data.get("notities", {}).get(dag, "")
    uur = datetime.now().hour
    waarschuwing = uur >= 19 and kcal_nog > 600

    return render_template("index.html",
        dagboek=dagboek_vandaag,
        vast_ontbijt=VAST_ONTBIJT,
        kcal_gehad=kcal_gehad,
        eiwit_gehad=eiwit_gehad,
        kcal_nog=kcal_nog,
        eiwit_nog=eiwit_nog,
        kcal_doel=PROFIEL["kcal_doel"],
        eiwit_doel=PROFIEL["eiwit_doel"],
        voorraad=data["voorraad"],
        boodschappenlijst=data["boodschappenlijst"],
        categorieen=list(CATEGORIEEN.keys()) + ["Overig"],
        snelproducten=list(VOEDINGSWAARDEN.keys()),
        favorieten=data.get("favorieten", []),
        streak=streak,
        week=week,
        water=water_vandaag,
        notitie=notitie_vandaag,
        waarschuwing=waarschuwing,
        naam=PROFIEL["naam"],
        datum=date.today().strftime("%A %d %B")
    )

@app.route("/schat_voeding", methods=["POST"])
def schat_voeding():
    naam = request.form.get("naam")
    if naam in VOEDINGSWAARDEN:
        return jsonify(VOEDINGSWAARDEN[naam])
    prompt = f"Schat voedingswaarden van: {naam}. Geef ALLEEN JSON: {{\"kcal\": 400, \"eiwit\": 30}}"
    response = ollama.chat(model="llama3.2:1b", messages=[{"role": "user", "content": prompt}])
    tekst = response["message"]["content"]
    match = re.search(r'\{"kcal":\s*(\d+),\s*"eiwit":\s*(\d+)\}', tekst)
    if match:
        return jsonify({"kcal": int(match.group(1)), "eiwit": int(match.group(2))})
    return jsonify({"kcal": 0, "eiwit": 0})

@app.route("/voeg_maaltijd_toe", methods=["POST"])
def voeg_maaltijd_toe():
    data = laad_data()
    dag = vandaag()
    if dag not in data["dagboek"]:
        data["dagboek"][dag] = []
    maaltijd = {
        "naam": request.form.get("naam"),
        "kcal": int(request.form.get("kcal", 0)),
        "eiwit": int(request.form.get("eiwit", 0)),
        "type": request.form.get("type", "overig"),
        "id": str(len(data["dagboek"][dag]))
    }
    data["dagboek"][dag].append(maaltijd)
    sla_op(data)
    return jsonify({"status": "ok", "kcal": maaltijd["kcal"], "eiwit": maaltijd["eiwit"]})

@app.route("/verwijder_maaltijd", methods=["POST"])
def verwijder_maaltijd():
    data = laad_data()
    dag = vandaag()
    index = int(request.form.get("index"))
    if dag in data["dagboek"] and 0 <= index < len(data["dagboek"][dag]):
        data["dagboek"][dag].pop(index)
    sla_op(data)
    return jsonify({"status": "ok"})

@app.route("/voeg_favoriet_toe", methods=["POST"])
def voeg_favoriet_toe():
    data = laad_data()
    favoriet = {
        "naam": request.form.get("naam"),
        "kcal": int(request.form.get("kcal", 0)),
        "eiwit": int(request.form.get("eiwit", 0))
    }
    namen = [f["naam"] for f in data.get("favorieten", [])]
    if favoriet["naam"] not in namen:
        if "favorieten" not in data:
            data["favorieten"] = []
        data["favorieten"].append(favoriet)
        sla_op(data)
    return jsonify({"status": "ok"})

@app.route("/voeg_boodschap_toe", methods=["POST"])
def voeg_boodschap_toe():
    data = laad_data()
    naam = request.form.get("naam")
    categorie = request.form.get("categorie") or bepaal_categorie(naam)
    item = {"naam": naam, "categorie": categorie, "gekocht": False}
    namen = [b["naam"].lower() for b in data["boodschappenlijst"]]
    if naam.lower() not in namen:
        data["boodschappenlijst"].append(item)
        sla_op(data)
    return jsonify({"status": "ok"})

@app.route("/markeer_gekocht", methods=["POST"])
def markeer_gekocht():
    data = laad_data()
    naam = request.form.get("naam")
    for item in data["boodschappenlijst"]:
        if item["naam"] == naam:
            item["gekocht"] = True
            if naam not in data["voorraad"]:
                data["voorraad"].append(naam)
    data["boodschappenlijst"] = [b for b in data["boodschappenlijst"] if not b["gekocht"]]
    sla_op(data)
    return jsonify({"status": "ok"})

@app.route("/verwijder_voorraad", methods=["POST"])
def verwijder_voorraad():
    data = laad_data()
    naam = request.form.get("naam")
    data["voorraad"] = [v for v in data["voorraad"] if v != naam]
    sla_op(data)
    return jsonify({"status": "ok", "naam": naam})

@app.route("/voeg_voorraad_toe", methods=["POST"])
def voeg_voorraad_toe():
    data = laad_data()
    naam = request.form.get("naam")
    if naam and naam not in data["voorraad"]:
        data["voorraad"].append(naam)
        sla_op(data)
    return jsonify({"status": "ok"})

@app.route("/water", methods=["POST"])
def water():
    data = laad_data()
    dag = vandaag()
    if "water" not in data:
        data["water"] = {}
    actie = request.form.get("actie")
    huidig = data["water"].get(dag, 0)
    if actie == "plus":
        data["water"][dag] = huidig + 1
    elif actie == "min" and huidig > 0:
        data["water"][dag] = huidig - 1
    sla_op(data)
    return jsonify({"water": data["water"][dag]})

@app.route("/notitie", methods=["POST"])
def notitie():
    data = laad_data()
    dag = vandaag()
    if "notities" not in data:
        data["notities"] = {}
    data["notities"][dag] = request.form.get("tekst", "")
    sla_op(data)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, port=5001, host="0.0.0.0")