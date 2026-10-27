"""Score d'urgence par règles explicites. Aide à la décision, à valider par un soignant.
Les seuils sont des hypothèses de départ à faire valider par un clinicien."""
from . import service

URGENT_THRESHOLD = 7
PRIORITY_THRESHOLD = 4
LABELS = {"urgent": "Urgent", "priority": "Prioritaire", "standard": "Standard"}


def _group_points(cluster):
    """0 à 3 points selon la réadmission du groupe, comparée aux autres groupes."""
    cl = service.clusters()
    rates = [c["readmission_pct"] for c in cl.values()]
    mine = cl.get(str(cluster), {}).get("readmission_pct")
    if not rates or mine is None or max(rates) == min(rates):
        return 0
    return round((mine - min(rates)) / (max(rates) - min(rates)) * 3)


def evaluate(raw, cluster, type_rdv=""):
    score, reasons = 0, []

    pts = _group_points(cluster)
    if pts:
        score += pts
        reasons.append(f"Groupe {cluster} à risque de réadmission élevé (+{pts})")

    em = raw["number_emergency"]
    if em >= 3:
        score += 3; reasons.append(f"{em} passages aux urgences l'an dernier (+3)")
    elif em >= 1:
        score += 2; reasons.append(f"{em} passage(s) aux urgences l'an dernier (+2)")

    inp = raw["number_inpatient"]
    if inp >= 2:
        score += 2; reasons.append(f"{inp} hospitalisations l'an dernier (+2)")
    elif inp == 1:
        score += 1; reasons.append("1 hospitalisation l'an dernier (+1)")

    a1c = raw["nominal"].get("A1Cresult", "None")
    if a1c == ">8":
        score += 2; reasons.append("HbA1c > 8 (+2)")
    elif a1c == ">7":
        score += 1; reasons.append("HbA1c > 7 (+1)")

    glu = raw["nominal"].get("max_glu_serum", "None")
    if glu == ">300":
        score += 2; reasons.append("Glycémie maximale > 300 (+2)")
    elif glu == ">200":
        score += 1; reasons.append("Glycémie maximale > 200 (+1)")

    if raw["insulin_state"] in ("Up", "Down"):
        score += 1; reasons.append("Dose d'insuline modifiée (+1)")

    if type_rdv == "urgence":
        level = "urgent"
        reasons.append("Type de RDV « Urgence » : urgent d'office")
    elif score >= URGENT_THRESHOLD:
        level = "urgent"
    elif score >= PRIORITY_THRESHOLD:
        level = "priority"
    else:
        level = "standard"

    return {"score": score, "level": level, "label": LABELS[level], "reasons": reasons}