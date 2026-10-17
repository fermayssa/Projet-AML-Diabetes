# =====================================================================
# CELLULE À AJOUTER À LA FIN DU NOTEBOOK : export du modèle pour Flask
# (à exécuter APRÈS la partie 16, quand K-Means est le modèle retenu)
# =====================================================================
import json, re, joblib, sklearn
from pathlib import Path

assert CHOSEN == "K-Means", "Cet export est prévu pour K-Means ; adapter si un autre algorithme est retenu."

OUT = Path("artifacts"); OUT.mkdir(exist_ok=True)
idx = X_train.index

# 1) Bornes de plafonnement, calculées sur le train AVANT plafonnement
caps = {}
for c in num_cols:
    if c == 'age':
        continue
    lo, hi = df_model.loc[idx, c].quantile([0.01, 0.99])
    caps[c] = [float(lo), float(hi)]

# 2) Valeurs typiques du train (utilisées pour les champs non demandés dans le formulaire)
defaults = {c: float(v) for c, v in X_train.median().items()}

# 3) Catégories possibles et valeur la plus fréquente de chaque variable nominale
categories = {c: sorted(map(str, df.loc[idx, c].unique())) for c in nominal}
modes = {c: str(df.loc[idx, c].mode().iloc[0]) for c in nominal}

# 4) Médicaments, du plus au moins fréquent
med_prevalence = df.loc[idx, med_cols].mean().sort_values(ascending=False)

# 5) Description des clusters  (>>> À VÉRIFIER / MODIFIER selon VOS résultats <<<)
CLUSTER_INFO = {
    0: ("Grands consommateurs de soins",
        "Nombreuses visites et hospitalisations antérieures.",
        "Suivi post-sortie renforcé, gestionnaire de cas."),
    1: ("Parcours simple et stable",
        "Séjour court, peu de médicaments, traitement stable.",
        "Parcours standard, éducation thérapeutique de base."),
    2: ("Séjour très court avec procédures",
        "Séjour très court, nombreuses procédures, retour à domicile fréquent.",
        "Sortie programmée, suivi léger."),
    3: ("Séjour long, complexe, traitement instable",
        "Séjour long, nombreux médicaments, changements de traitement.",
        "Revue pharmaceutique, diabétologue référent."),
}
sizes = pd.Series(labels_train).value_counts(normalize=True).sort_index() * 100
rates = pd.Series(y_post_train.values).groupby(labels_train).mean() * 100
clusters = {}
for k in range(BEST_K):
    nom, desc, action = CLUSTER_INFO.get(k, (f"Cluster {k}", "", ""))
    clusters[str(k)] = {"name": nom, "description": desc, "action": action,
                        "size_pct": round(float(sizes[k]), 1),
                        "readmission_pct": round(float(rates[k]), 1)}

# 6) Sauvegarde
config = {
    "columns": X_train.columns.tolist(),      # ordre exact des colonnes du modèle
    "num_cols": num_cols,
    "features_cl": features_cl,
    "caps": caps,
    "defaults": defaults,
    "categories": categories,
    "modes": modes,
    "med_cols": med_cols,
    "med_order": med_prevalence.index.tolist(),
    "clusters": clusters,
    "versions": {"sklearn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__},
}
(OUT / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
joblib.dump({"km": km, "pca": pca, "scaler": scaler}, OUT / "model.joblib")
print("Fichiers exportés dans", OUT.resolve(), ":", [p.name for p in OUT.iterdir()])
print("Version de scikit-learn :", sklearn.__version__, "(à reprendre dans requirements.txt)")

# 7) (Google Colab) télécharger le dossier sur votre PC
try:
    import shutil
    from google.colab import files
    shutil.make_archive("artifacts", "zip", OUT)
    files.download("artifacts.zip")
except ImportError:
    pass
