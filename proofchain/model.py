import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from .config import MODEL_PATH
from .features import features
from .tamper import TAMPER_FNS, legit_edit


def build_dataset(master, n=200, seed=1000):
    """n/2 documented (clean) versions + n/2 silently tampered versions."""
    rows = []
    for i in range(n):
        rng = np.random.default_rng(seed + i)
        frac = 10 ** rng.uniform(-3, np.log10(0.08))      # 0.1% .. 8% of rows
        if i % 2 == 0:
            v = legit_edit(master, frac, seed=i) if rng.random() < 0.7 else master.copy()
            label = 0
        else:
            v = master.copy()
            for k in rng.choice(len(TAMPER_FNS), size=int(rng.integers(1, 4)), replace=False):
                v = TAMPER_FNS[k](v, frac, seed=i)
            label = 1
        rows.append({**features(v, master), "label": label})
    return pd.DataFrame(rows)


def train(feat):
    X, y = feat.drop(columns="label"), feat["label"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)
    clf = RandomForestClassifier(n_estimators=200, random_state=0).fit(Xtr, ytr)
    pred = clf.predict(Xte)
    report = classification_report(yte, pred, target_names=["clean", "tampered"])
    cm = confusion_matrix(yte, pred)
    importances = pd.Series(clf.feature_importances_, index=X.columns).sort_values(ascending=False)
    iso = IsolationForest(random_state=0).fit(X[y == 0])
    bundle = {"clf": clf, "iso": iso, "columns": list(X.columns)}
    return bundle, report, cm, importances


def save_bundle(bundle):
    joblib.dump(bundle, MODEL_PATH)


def load_bundle():
    return joblib.load(MODEL_PATH)
