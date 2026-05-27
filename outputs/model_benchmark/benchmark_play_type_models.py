import argparse
import json
import sqlite3
import time
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import (
    AdaBoostClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import (
    LogisticRegression,
    PassiveAggressiveClassifier,
    Perceptron,
    RidgeClassifier,
    SGDClassifier,
)
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import BernoulliNB, GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier, ExtraTreeClassifier


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nflpredictor" / "db.sqlite3"
OUT_DIR = ROOT / "outputs" / "model_benchmark"
RANDOM_STATE = 42


FEATURES = [
    "down",
    "ydstogo",
    "yardline_100",
    "quarter",
    "game_seconds_remaining",
    "score_differential",
    "posteam_type",
    "defteam",
    "posteam",
    "is_losing",
    "short_yardage",
    "late_game",
    "medium_yardage",
    "long_yardage",
    "quarter_half",
    "clock_pressure",
    "red_zone",
    "season",
    "shotgun",
    "no_huddle",
    "goal_to_go",
    "defteam_timeouts_remaining",
    "posteam_timeouts_remaining",
    "half_seconds_remaining",
    "quarter_seconds_remaining",
]


def load_data(max_rows):
    query = """
        SELECT
            p.down,
            p.ydstogo,
            p.yardline_100,
            p.quarter,
            p.game_seconds_remaining,
            p.score_differential,
            p.posteam_type,
            p.defteam,
            t.team_abbr AS posteam,
            p.is_losing,
            p.short_yardage,
            p.late_game,
            p.medium_yardage,
            p.long_yardage,
            p.quarter_half,
            p.clock_pressure,
            p.red_zone,
            p.season,
            p.shotgun,
            p.no_huddle,
            p.goal_to_go,
            p.defteam_timeouts_remaining,
            p.posteam_timeouts_remaining,
            p.half_seconds_remaining,
            p.quarter_seconds_remaining,
            p.play_type
        FROM core_play p
        JOIN core_team t ON t.id = p.posteam_id
        WHERE p.play_type IN ('pass', 'run', 'punt', 'field_goal')
    """
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(query, conn)

    if max_rows and len(df) > max_rows:
        df, _ = train_test_split(
            df,
            train_size=max_rows,
            stratify=df["play_type"],
            random_state=RANDOM_STATE,
        )

    return df.reset_index(drop=True)


def prepare_matrix(df):
    X = df[FEATURES].copy()
    y = df["play_type"].copy()

    bool_cols = [
        "is_losing",
        "short_yardage",
        "late_game",
        "medium_yardage",
        "long_yardage",
        "clock_pressure",
        "red_zone",
        "shotgun",
        "no_huddle",
        "goal_to_go",
    ]
    for col in bool_cols:
        X.loc[:, col] = X[col].fillna(False).astype(int)

    numeric_cols = X.columns.difference(["posteam_type", "defteam", "posteam"])
    X.loc[:, numeric_cols] = X[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    X.loc[:, ["posteam_type", "defteam", "posteam"]] = X[
        ["posteam_type", "defteam", "posteam"]
    ].fillna("unknown")

    X = pd.get_dummies(X, columns=["posteam_type", "defteam", "posteam"], drop_first=True)
    return X.astype(float), y


def model_specs():
    return {
        "Dummy most-frequent": DummyClassifier(strategy="most_frequent"),
        "Logistic Regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1500, class_weight="balanced", n_jobs=1),
        ),
        "Ridge Classifier": make_pipeline(
            StandardScaler(),
            RidgeClassifier(class_weight="balanced"),
        ),
        "SGD log-loss": make_pipeline(
            StandardScaler(),
            SGDClassifier(
                loss="log_loss",
                alpha=0.0001,
                max_iter=1500,
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=1,
            ),
        ),
        "SGD hinge": make_pipeline(
            StandardScaler(),
            SGDClassifier(
                loss="hinge",
                alpha=0.0001,
                max_iter=1500,
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=1,
            ),
        ),
        "Passive Aggressive": make_pipeline(
            StandardScaler(),
            PassiveAggressiveClassifier(
                max_iter=1500,
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=1,
            ),
        ),
        "Perceptron": make_pipeline(
            StandardScaler(),
            Perceptron(
                max_iter=1500,
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=1,
            ),
        ),
        "Linear SVC": make_pipeline(
            StandardScaler(),
            LinearSVC(class_weight="balanced", random_state=RANDOM_STATE, max_iter=3000),
        ),
        "Gaussian NB": make_pipeline(StandardScaler(), GaussianNB()),
        "Bernoulli NB": make_pipeline(MinMaxScaler(), BernoulliNB()),
        "KNN": make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=35, n_jobs=1)),
        "Decision Tree": DecisionTreeClassifier(
            max_depth=18,
            min_samples_leaf=25,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        "Extra Tree": ExtraTreeClassifier(
            max_depth=18,
            min_samples_leaf=25,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=180,
            max_depth=18,
            min_samples_leaf=4,
            class_weight="balanced_subsample",
            random_state=RANDOM_STATE,
            n_jobs=1,
        ),
        "Extra Trees": ExtraTreesClassifier(
            n_estimators=220,
            max_depth=18,
            min_samples_leaf=4,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=1,
        ),
        "Hist Gradient Boosting": HistGradientBoostingClassifier(
            max_iter=180,
            learning_rate=0.08,
            l2_regularization=0.05,
            random_state=RANDOM_STATE,
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=120,
            learning_rate=0.08,
            max_depth=4,
            random_state=RANDOM_STATE,
        ),
        "AdaBoost": AdaBoostClassifier(
            n_estimators=160,
            learning_rate=0.08,
            random_state=RANDOM_STATE,
        ),
    }


def benchmark_models(X_train, X_test, y_train, y_test):
    rows = []
    for name, model in model_specs().items():
        estimator = clone(model)
        print(f"Running {name}...", flush=True)
        try:
            fit_start = time.perf_counter()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ConvergenceWarning)
                estimator.fit(X_train, y_train)
            fit_seconds = time.perf_counter() - fit_start

            predict_start = time.perf_counter()
            y_pred = estimator.predict(X_test)
            predict_seconds = time.perf_counter() - predict_start

            rows.append(
                {
                    "model": name,
                    "accuracy": accuracy_score(y_test, y_pred),
                    "macro_f1": f1_score(y_test, y_pred, average="macro"),
                    "weighted_f1": f1_score(y_test, y_pred, average="weighted"),
                    "fit_seconds": fit_seconds,
                    "predict_seconds": predict_seconds,
                    "status": "ok",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "model": name,
                    "accuracy": np.nan,
                    "macro_f1": np.nan,
                    "weighted_f1": np.nan,
                    "fit_seconds": np.nan,
                    "predict_seconds": np.nan,
                    "status": f"failed: {exc}",
                }
            )
    return pd.DataFrame(rows)


def plot_results(results):
    ok = results[results["status"] == "ok"].copy()
    ok = ok.sort_values("macro_f1", ascending=True)

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(16, 9), gridspec_kw={"width_ratios": [1.25, 1]})
    colors = ["#4E79A7" if model != "Random Forest" else "#E15759" for model in ok["model"]]

    axes[0].barh(ok["model"], ok["macro_f1"], color=colors)
    axes[0].set_title("Play-Type Prediction Quality")
    axes[0].set_xlabel("Macro F1")
    axes[0].set_xlim(max(0, ok["macro_f1"].min() - 0.05), min(1.0, ok["macro_f1"].max() + 0.05))

    axes[1].scatter(ok["fit_seconds"], ok["macro_f1"], s=90, c=colors, alpha=0.9)
    for _, row in ok.iterrows():
        axes[1].annotate(
            row["model"],
            (row["fit_seconds"], row["macro_f1"]),
            fontsize=8,
            xytext=(5, 4),
            textcoords="offset points",
        )
    axes[1].set_xscale("log")
    axes[1].set_title("Quality vs Training Time")
    axes[1].set_xlabel("Fit seconds, log scale")
    axes[1].set_ylabel("Macro F1")

    fig.suptitle("NFL Play-by-Play Model Benchmark", fontsize=16, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = OUT_DIR / "model_benchmark_results.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-rows", type=int, default=100_000)
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data(args.max_rows)
    X, y = prepare_matrix(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=args.test_size,
        stratify=y,
        random_state=RANDOM_STATE,
    )

    results = benchmark_models(X_train, X_test, y_train, y_test)
    results = results.sort_values(["macro_f1", "fit_seconds"], ascending=[False, True])
    csv_path = OUT_DIR / "model_benchmark_results.csv"
    json_path = OUT_DIR / "model_benchmark_metadata.json"
    results.to_csv(csv_path, index=False)
    plot_path = plot_results(results)

    metadata = {
        "db_path": str(DB_PATH),
        "rows_used": int(len(df)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "feature_count_after_encoding": int(X.shape[1]),
        "target_distribution": y.value_counts().to_dict(),
        "csv_path": str(csv_path),
        "plot_path": str(plot_path),
    }
    json_path.write_text(json.dumps(metadata, indent=2))

    print("\nResults:")
    print(results.to_string(index=False))
    print(f"\nSaved CSV: {csv_path}")
    print(f"Saved plot: {plot_path}")
    print(f"Saved metadata: {json_path}")


if __name__ == "__main__":
    main()
