import pandas as pd


def preparer(df_in, cfg):
    # df_in : DataFrame de patients bruts. Colonnes absentes -> valeur typique (médiane / modalité la plus fréquente).
    df = pd.DataFrame(df_in).copy()
    for c in cfg['num_cols']:
        if c not in df.columns:
            df[c] = cfg['defaults'][c]
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(cfg['defaults'][c])
    for c in cfg['nominal']:
        if c not in df.columns:
            df[c] = cfg['modes'][c]
        df[c] = df[c].astype(str)
        df.loc[~df[c].isin(cfg['categories'][c]), c] = cfg['modes'][c]
    # pas de drop_first ici : reindex ne garde que les colonnes connues du modèle
    X = pd.get_dummies(df[cfg['num_cols'] + cfg['nominal']])
    X = X.reindex(columns=cfg['columns'], fill_value=0)
    dummies = [c for c in X.columns if c not in cfg['num_cols']]
    X[dummies] = X[dummies].astype(cfg['dummies_dtype'])
    return X
