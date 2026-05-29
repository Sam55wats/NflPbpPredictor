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
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


warnings.filterwarnings("ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nflpredictor" / "db.sqlite3"
OUT_DIR = ROOT / "outputs" / "feature_experiments"
RANDOM_STATE = 42
HOLDOUT_SEASON = 2024
LABELS = ["field_goal", "pass", "punt", "run"]


BASE_FEATURES = [
    "down",
    "ydstogo",
    "yardline_100",
    "quarter",
    "game_seconds_remaining",
    "score_differential",
    "posteam_type",
    "defteam",
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

BUCKET_FEATURES = ["short_yardage", "medium_yardage", "long_yardage"]
TENDENCY_FEATURES = [
    "offense_down_pass_rate",
    "offense_down_run_rate",
    "offense_red_zone_pass_rate",
    "offense_red_zone_run_rate",
    "offense_fourth_down_punt_rate",
    "offense_fg_range_field_goal_rate",
    "defense_down_pass_rate_allowed",
    "defense_down_run_rate_allowed",
    "defense_red_zone_pass_rate_allowed",
    "defense_red_zone_run_rate_allowed",
]

ROLLING_TENDENCY_FEATURES = [
    "rolling_offense_down_pass_rate",
    "rolling_offense_down_run_rate",
    "rolling_offense_red_zone_pass_rate",
    "rolling_offense_red_zone_run_rate",
    "rolling_offense_fourth_down_punt_rate",
    "rolling_offense_fg_range_field_goal_rate",
    "rolling_defense_down_pass_rate_allowed",
    "rolling_defense_down_run_rate_allowed",
    "rolling_defense_red_zone_pass_rate_allowed",
    "rolling_defense_red_zone_run_rate_allowed",
]

BOOL_FEATURES = [
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

CATEGORICAL_FEATURES = ["posteam_type", "defteam", "posteam"]


def load_data():
    query = """
        SELECT
            p.id,
            p.down,
            p.ydstogo,
            p.yardline_100,
            p.quarter,
            p.game_seconds_remaining,
            p.score_differential,
            p.posteam_type AS stored_posteam_type,
            p.defteam AS stored_defteam,
            t.team_abbr AS posteam,
            p.is_losing AS stored_is_losing,
            p.short_yardage AS stored_short_yardage,
            p.late_game AS stored_late_game,
            p.medium_yardage AS stored_medium_yardage,
            p.long_yardage AS stored_long_yardage,
            p.quarter_half AS stored_quarter_half,
            p.clock_pressure AS stored_clock_pressure,
            p.red_zone AS stored_red_zone,
            p.season AS stored_season,
            p.shotgun,
            p.no_huddle,
            p.goal_to_go,
            p.defteam_timeouts_remaining,
            p.posteam_timeouts_remaining,
            p.half_seconds_remaining,
            p.quarter_seconds_remaining,
            p.play_type,
            g.week,
            s.year AS season,
            ht.team_abbr AS home_team,
            at.team_abbr AS away_team
        FROM core_play p
        JOIN core_team t ON t.id = p.posteam_id
        JOIN core_game g ON g.id = p.game_id
        JOIN core_season s ON s.id = g.season_id
        JOIN core_team ht ON ht.id = g.home_team_id
        JOIN core_team at ON at.id = g.away_team_id
        WHERE p.play_type IN ('pass', 'run', 'punt', 'field_goal')
    """
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(query, conn)
    return df


def recompute_features(df):
    df = df.copy()
    numeric_cols = [
        "down",
        "ydstogo",
        "yardline_100",
        "quarter",
        "game_seconds_remaining",
        "score_differential",
        "shotgun",
        "no_huddle",
        "goal_to_go",
        "defteam_timeouts_remaining",
        "posteam_timeouts_remaining",
        "half_seconds_remaining",
        "quarter_seconds_remaining",
        "season",
        "week",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["is_losing"] = (df["score_differential"] < 0).astype(int)
    df["short_yardage"] = (df["ydstogo"] <= 3).astype(int)
    df["medium_yardage"] = ((df["ydstogo"] > 3) & (df["ydstogo"] <= 7)).astype(int)
    df["long_yardage"] = (df["ydstogo"] > 7).astype(int)
    df["quarter_half"] = (df["quarter"] <= 2).astype(int)
    df["clock_pressure"] = (df["half_seconds_remaining"] <= 120).astype(int)
    df["red_zone"] = (df["yardline_100"] <= 20).astype(int)
    df["late_game"] = (df["game_seconds_remaining"] <= 120).astype(int)
    df["posteam_type"] = np.where(df["posteam"] == df["home_team"], "home", "away")
    df["defteam"] = np.where(df["posteam"] == df["home_team"], df["away_team"], df["home_team"])
    df["fg_range"] = (df["yardline_100"] <= 40).astype(int)
    return df


def verify_stored_features(df):
    checks = {
        "red_zone": df["red_zone"],
        "clock_pressure": df["clock_pressure"],
        "short_yardage": df["short_yardage"],
        "medium_yardage": df["medium_yardage"],
        "long_yardage": df["long_yardage"],
        "is_losing": df["is_losing"],
        "late_game": df["late_game"],
        "quarter_half": df["quarter_half"],
        "season": df["season"],
        "posteam_type": df["posteam_type"],
        "defteam": df["defteam"],
    }
    rows = []
    for name, expected in checks.items():
        stored_name = f"stored_{name}"
        stored = df[stored_name] if stored_name in df else pd.Series([np.nan] * len(df))
        if name in {"posteam_type", "defteam"}:
            mismatch = stored.fillna("unknown").astype(str) != expected.fillna("unknown").astype(str)
            stored_unique = ", ".join(map(str, sorted(stored.fillna("NULL").astype(str).unique())[:6]))
        else:
            stored_num = pd.to_numeric(stored, errors="coerce")
            expected_num = pd.to_numeric(expected, errors="coerce")
            mismatch = stored_num.fillna(-999999).astype(float) != expected_num.fillna(-999999).astype(float)
            stored_unique = ", ".join(map(str, sorted(stored_num.dropna().unique())[:6]))
        rows.append(
            {
                "feature": name,
                "mismatches": int(mismatch.sum()),
                "mismatch_rate": float(mismatch.mean()),
                "stored_unique_sample": stored_unique,
            }
        )
    return pd.DataFrame(rows)


def add_tendency_features(train_df, test_df):
    train_df = train_df.copy()
    test_df = test_df.copy()
    global_rates = train_df["play_type"].value_counts(normalize=True).to_dict()

    def add_rate(train, test, keys, play_type, name):
        group = train.assign(target=(train["play_type"] == play_type).astype(float)).groupby(keys)["target"].mean()
        default = global_rates.get(play_type, 0.0)
        train[name] = train.set_index(keys).index.map(group).fillna(default).astype(float)
        test[name] = test.set_index(keys).index.map(group).fillna(default).astype(float)

    add_rate(train_df, test_df, ["posteam", "down"], "pass", "offense_down_pass_rate")
    add_rate(train_df, test_df, ["posteam", "down"], "run", "offense_down_run_rate")
    add_rate(train_df, test_df, ["posteam", "red_zone"], "pass", "offense_red_zone_pass_rate")
    add_rate(train_df, test_df, ["posteam", "red_zone"], "run", "offense_red_zone_run_rate")
    add_rate(train_df, test_df, ["posteam", "down"], "punt", "offense_fourth_down_punt_rate")
    add_rate(train_df, test_df, ["posteam", "fg_range"], "field_goal", "offense_fg_range_field_goal_rate")
    add_rate(train_df, test_df, ["defteam", "down"], "pass", "defense_down_pass_rate_allowed")
    add_rate(train_df, test_df, ["defteam", "down"], "run", "defense_down_run_rate_allowed")
    add_rate(train_df, test_df, ["defteam", "red_zone"], "pass", "defense_red_zone_pass_rate_allowed")
    add_rate(train_df, test_df, ["defteam", "red_zone"], "run", "defense_red_zone_run_rate_allowed")
    return train_df, test_df


def add_rolling_tendency_features(df):
    df = df.copy().sort_values(["season", "week", "id"]).reset_index(drop=True)
    prior_rates = {
        "pass": 0.53,
        "run": 0.38,
        "punt": 0.06,
        "field_goal": 0.03,
    }
    specs = [
        (["posteam", "down"], "pass", "rolling_offense_down_pass_rate"),
        (["posteam", "down"], "run", "rolling_offense_down_run_rate"),
        (["posteam", "red_zone"], "pass", "rolling_offense_red_zone_pass_rate"),
        (["posteam", "red_zone"], "run", "rolling_offense_red_zone_run_rate"),
        (["posteam", "down"], "punt", "rolling_offense_fourth_down_punt_rate"),
        (["posteam", "fg_range"], "field_goal", "rolling_offense_fg_range_field_goal_rate"),
        (["defteam", "down"], "pass", "rolling_defense_down_pass_rate_allowed"),
        (["defteam", "down"], "run", "rolling_defense_down_run_rate_allowed"),
        (["defteam", "red_zone"], "pass", "rolling_defense_red_zone_pass_rate_allowed"),
        (["defteam", "red_zone"], "run", "rolling_defense_red_zone_run_rate_allowed"),
    ]

    for feature in ROLLING_TENDENCY_FEATURES:
        df[feature] = np.nan

    previous_seasons = df.iloc[0:0].copy()
    for season in sorted(df["season"].dropna().unique()):
        season_mask = df["season"] == season
        current_season_history = df.iloc[0:0].copy()

        for week in sorted(df.loc[season_mask, "week"].dropna().unique()):
            week_mask = season_mask & (df["week"] == week)
            batch = df.loc[week_mask]

            all_prior = pd.concat([previous_seasons, current_season_history], ignore_index=True)
            for keys, play_type, feature in specs:
                fallback = prior_rates[play_type]
                if not all_prior.empty:
                    fallback = float((all_prior["play_type"] == play_type).mean())

                values = pd.Series(fallback, index=batch.index, dtype=float)

                if not previous_seasons.empty:
                    previous_group = (
                        previous_seasons.assign(target=(previous_seasons["play_type"] == play_type).astype(float))
                        .groupby(keys)["target"]
                        .mean()
                    )
                    previous_values = batch.set_index(keys).index.map(previous_group)
                    values = pd.Series(previous_values, index=batch.index).fillna(values).astype(float)

                if not current_season_history.empty:
                    current_group = (
                        current_season_history.assign(
                            target=(current_season_history["play_type"] == play_type).astype(float)
                        )
                        .groupby(keys)["target"]
                        .mean()
                    )
                    current_values = batch.set_index(keys).index.map(current_group)
                    values = pd.Series(current_values, index=batch.index).fillna(values).astype(float)

                df.loc[week_mask, feature] = values

            current_season_history = pd.concat([current_season_history, batch], ignore_index=True)

        previous_seasons = pd.concat([previous_seasons, df.loc[season_mask]], ignore_index=True)

    return df


def prepare_matrix(train_df, test_df, features):
    train_x = train_df[features].copy()
    test_x = test_df[features].copy()
    combined = pd.concat([train_x, test_x], axis=0, ignore_index=True)

    for col in BOOL_FEATURES:
        if col in combined:
            combined[col] = combined[col].fillna(False).astype(int)

    for col in CATEGORICAL_FEATURES:
        if col in combined:
            combined[col] = combined[col].fillna("unknown").astype(str)

    numeric_cols = combined.columns.difference([c for c in CATEGORICAL_FEATURES if c in combined])
    combined[numeric_cols] = combined[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    combined = pd.get_dummies(combined, columns=[c for c in CATEGORICAL_FEATURES if c in combined], drop_first=True)
    combined = combined.astype(float)
    train_encoded = combined.iloc[: len(train_df)].copy()
    test_encoded = combined.iloc[len(train_df) :].copy()
    return train_encoded, test_encoded


def rf_model():
    return RandomForestClassifier(
        n_estimators=140,
        max_depth=18,
        min_samples_leaf=4,
        min_samples_split=2,
        max_features="sqrt",
        class_weight="balanced_subsample",
        random_state=RANDOM_STATE,
        n_jobs=1,
    )


def logistic_model():
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1500, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=1),
    )


def fit_predict_by_team(train_df, test_df, features, estimator):
    preds = pd.Series(index=test_df.index, dtype=object)
    fit_seconds = 0.0
    for team in sorted(test_df["posteam"].unique()):
        train_team = train_df[train_df["posteam"] == team]
        test_team = test_df[test_df["posteam"] == team]
        if train_team.empty or test_team.empty:
            continue
        x_train, x_test = prepare_matrix(train_team, test_team, features)
        model = clone(estimator)
        start = time.perf_counter()
        model.fit(x_train, train_team["play_type"])
        fit_seconds += time.perf_counter() - start
        preds.loc[test_team.index] = model.predict(x_test)
    return preds.fillna(train_df["play_type"].mode().iloc[0]), fit_seconds


def fit_predict_global(train_df, test_df, features, estimator):
    x_train, x_test = prepare_matrix(train_df, test_df, features + ["posteam"])
    x_train, x_test = align_global_posteam_columns(x_train, x_test)
    model = clone(estimator)
    start = time.perf_counter()
    model.fit(x_train, train_df["play_type"])
    fit_seconds = time.perf_counter() - start
    return pd.Series(model.predict(x_test), index=test_df.index), fit_seconds


def align_global_posteam_columns(x_train, x_test):
    return x_train, x_test


def staged_rf_predictions(train_df, test_df, features):
    preds = pd.Series(index=test_df.index, dtype=object)
    fit_seconds = 0.0
    for team in sorted(test_df["posteam"].unique()):
        train_team = train_df[train_df["posteam"] == team].copy()
        test_team = test_df[test_df["posteam"] == team].copy()
        if train_team.empty or test_team.empty:
            continue

        x_train, x_test = prepare_matrix(train_team, test_team, features)
        stage_train = np.where(train_team["play_type"].isin(["pass", "run"]), "offense", "special")
        stage_model = rf_model()
        start = time.perf_counter()
        stage_model.fit(x_train, stage_train)
        stage_pred = stage_model.predict(x_test)
        fit_seconds += time.perf_counter() - start

        team_preds = pd.Series(index=test_team.index, dtype=object)
        for group_name, classes in [("offense", ["pass", "run"]), ("special", ["field_goal", "punt"])]:
            train_sub = train_team[train_team["play_type"].isin(classes)]
            target_index = test_team.index[stage_pred == group_name]
            if train_sub.empty or len(target_index) == 0:
                continue
            if train_sub["play_type"].nunique() == 1:
                team_preds.loc[target_index] = train_sub["play_type"].iloc[0]
                continue
            sub_model = rf_model()
            x_sub_train, x_sub_test = prepare_matrix(train_sub, test_team.loc[target_index], features)
            start = time.perf_counter()
            sub_model.fit(x_sub_train, train_sub["play_type"])
            fit_seconds += time.perf_counter() - start
            team_preds.loc[target_index] = sub_model.predict(x_sub_test)

        preds.loc[test_team.index] = team_preds.fillna(train_team["play_type"].mode().iloc[0])
    return preds.fillna(train_df["play_type"].mode().iloc[0]), fit_seconds


def score_predictions(name, y_true, y_pred, fit_seconds):
    report = classification_report(y_true, y_pred, labels=LABELS, output_dict=True, zero_division=0)
    row = {
        "experiment": name,
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, labels=LABELS, average="weighted", zero_division=0),
        "fit_seconds": fit_seconds,
    }
    for label in LABELS:
        row[f"f1_{label}"] = report[label]["f1-score"]
        row[f"recall_{label}"] = report[label]["recall"]
    return row


def score_predictions_by_team(name, test_df, y_pred):
    rows = []
    for team in sorted(test_df["posteam"].unique()):
        team_mask = test_df["posteam"] == team
        team_true = test_df.loc[team_mask, "play_type"]
        team_pred = y_pred.loc[team_mask]
        report = classification_report(team_true, team_pred, labels=LABELS, output_dict=True, zero_division=0)
        row = {
            "experiment": name,
            "team": team,
            "support": int(team_mask.sum()),
            "accuracy": accuracy_score(team_true, team_pred),
            "macro_f1": f1_score(team_true, team_pred, labels=LABELS, average="macro", zero_division=0),
            "weighted_f1": f1_score(team_true, team_pred, labels=LABELS, average="weighted", zero_division=0),
        }
        for label in LABELS:
            row[f"f1_{label}"] = report[label]["f1-score"]
            row[f"recall_{label}"] = report[label]["recall"]
        rows.append(row)
    return rows


def run_experiments(train_df, test_df):
    no_bucket_features = [f for f in BASE_FEATURES if f not in BUCKET_FEATURES]
    experiments = [
        ("RF current feature set", BASE_FEATURES, rf_model(), "team"),
        ("RF without yardage buckets", no_bucket_features, rf_model(), "team"),
        ("RF broad tendency features", BASE_FEATURES + TENDENCY_FEATURES, rf_model(), "team"),
        ("RF rolling tendencies no buckets", no_bucket_features + ROLLING_TENDENCY_FEATURES, rf_model(), "team"),
        ("Staged RF current features", BASE_FEATURES, None, "staged"),
        ("Staged RF no buckets", no_bucket_features, None, "staged"),
        ("Staged RF rolling tendencies no buckets", no_bucket_features + ROLLING_TENDENCY_FEATURES, None, "staged"),
        ("Simple logistic baseline", BASE_FEATURES, logistic_model(), "global"),
        ("Dummy most-frequent baseline", BASE_FEATURES, DummyClassifier(strategy="most_frequent"), "global"),
    ]
    rows = []
    predictions = {}
    y_true = test_df["play_type"]
    for name, features, estimator, mode in experiments:
        print(f"Running {name}...", flush=True)
        if mode == "team":
            y_pred, fit_seconds = fit_predict_by_team(train_df, test_df, features, estimator)
        elif mode == "staged":
            y_pred, fit_seconds = staged_rf_predictions(train_df, test_df, features)
        else:
            y_pred, fit_seconds = fit_predict_global(train_df, test_df, features, estimator)
        predictions[name] = y_pred
        rows.append(score_predictions(name, y_true, y_pred, fit_seconds))
    return pd.DataFrame(rows).sort_values("macro_f1", ascending=False), predictions


def permutation_importance_by_team(train_df, test_df, features, n_repeats=2):
    rng = np.random.default_rng(RANDOM_STATE)
    models = {}
    encoded = {}
    for team in sorted(test_df["posteam"].unique()):
        train_team = train_df[train_df["posteam"] == team]
        test_team = test_df[test_df["posteam"] == team]
        if train_team.empty or test_team.empty:
            continue
        x_train, x_test = prepare_matrix(train_team, test_team, features)
        model = rf_model()
        model.fit(x_train, train_team["play_type"])
        models[team] = model
        encoded[team] = (train_team, test_team, x_train, x_test)

    baseline_parts = []
    for team, model in models.items():
        _, test_team, _, x_test = encoded[team]
        baseline_parts.append(pd.Series(model.predict(x_test), index=test_team.index))
    baseline_pred = pd.concat(baseline_parts).sort_index()
    baseline_score = f1_score(
        test_df.loc[baseline_pred.index, "play_type"],
        baseline_pred,
        labels=LABELS,
        average="macro",
        zero_division=0,
    )

    rows = []
    for feature in features:
        scores = []
        for _ in range(n_repeats):
            pred_parts = []
            for team, model in models.items():
                train_team, test_team, _, _ = encoded[team]
                shuffled = test_team.copy()
                shuffled[feature] = rng.permutation(shuffled[feature].to_numpy())
                _, x_test_perm = prepare_matrix(train_team, shuffled, features)
                pred_parts.append(pd.Series(model.predict(x_test_perm), index=test_team.index))
            perm_pred = pd.concat(pred_parts).sort_index()
            score = f1_score(
                test_df.loc[perm_pred.index, "play_type"],
                perm_pred,
                labels=LABELS,
                average="macro",
                zero_division=0,
            )
            scores.append(score)
        rows.append(
            {
                "feature": feature,
                "baseline_macro_f1": baseline_score,
                "permuted_macro_f1": float(np.mean(scores)),
                "macro_f1_drop": float(baseline_score - np.mean(scores)),
            }
        )
    return pd.DataFrame(rows).sort_values("macro_f1_drop", ascending=False)


def plot_metric_bars(results):
    plot_df = results.sort_values("accuracy")
    y = np.arange(len(plot_df))
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.barh(y - 0.18, plot_df["accuracy"], height=0.36, label="Accuracy", color="#2563a7")
    ax.barh(y + 0.18, plot_df["macro_f1"], height=0.36, label="Macro F1", color="#13795b")
    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["experiment"])
    ax.set_xlabel("Score on 2024 holdout")
    ax.set_xlim(0, max(1.0, plot_df[["accuracy", "macro_f1"]].max().max() + 0.05))
    ax.set_title("Play-Type Model Experiment Results")
    ax.legend()
    fig.tight_layout()
    path = OUT_DIR / "experiment_accuracy_f1.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_bucket_delta(results):
    baseline = results.set_index("experiment").loc["RF current feature set"]
    no_bucket = results.set_index("experiment").loc["RF without yardage buckets"]
    metrics = ["accuracy", "macro_f1", "weighted_f1", "f1_pass", "f1_run", "f1_punt", "f1_field_goal"]
    delta = pd.DataFrame(
        {
            "metric": metrics,
            "delta_without_buckets": [no_bucket[m] - baseline[m] for m in metrics],
        }
    )
    fig, ax = plt.subplots(figsize=(11, 5.8))
    colors = np.where(delta["delta_without_buckets"] >= 0, "#13795b", "#b42318")
    ax.bar(delta["metric"], delta["delta_without_buckets"], color=colors)
    ax.axhline(0, color="#172026", linewidth=1)
    ax.set_title("Effect of Removing Yardage Bucket Features")
    ax.set_ylabel("Score change vs current RF")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    path = OUT_DIR / "yardage_bucket_ablation_delta.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    delta.to_csv(OUT_DIR / "yardage_bucket_ablation_delta.csv", index=False)
    return path


def plot_confusions(predictions, y_true):
    selected = [
        "RF current feature set",
        "RF without yardage buckets",
        "RF rolling tendencies no buckets",
        "Staged RF rolling tendencies no buckets",
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    for ax, name in zip(axes.flat, selected):
        cm = confusion_matrix(y_true, predictions[name], labels=LABELS, normalize="true")
        disp = ConfusionMatrixDisplay(cm, display_labels=LABELS)
        disp.plot(ax=ax, cmap="Blues", values_format=".2f", colorbar=False)
        ax.set_title(name)
        ax.tick_params(axis="x", rotation=25)
    fig.suptitle("Normalized Confusion Matrices on 2024 Holdout", weight="bold")
    fig.tight_layout()
    path = OUT_DIR / "confusion_matrices.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_permutation(perm):
    top = perm.head(15).sort_values("macro_f1_drop")
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(top["feature"], top["macro_f1_drop"], color="#13795b")
    ax.set_title("Permutation Importance: Current RF Feature Set")
    ax.set_xlabel("Macro F1 drop after shuffling feature")
    fig.tight_layout()
    path = OUT_DIR / "permutation_importance.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def write_html_report(results, verification, perm, paths, metadata):
    result_rows = "\n".join(
        f"<tr><td>{row.experiment}</td><td>{row.accuracy:.4f}</td><td>{row.macro_f1:.4f}</td>"
        f"<td>{row.weighted_f1:.4f}</td><td>{row.f1_pass:.4f}</td><td>{row.f1_run:.4f}</td>"
        f"<td>{row.f1_punt:.4f}</td><td>{row.f1_field_goal:.4f}</td></tr>"
        for row in results.itertuples()
    )
    verify_rows = "\n".join(
        f"<tr><td>{row.feature}</td><td>{row.mismatches}</td><td>{row.mismatch_rate:.1%}</td>"
        f"<td>{row.stored_unique_sample}</td></tr>"
        for row in verification.itertuples()
    )
    perm_rows = "\n".join(
        f"<tr><td>{row.feature}</td><td>{row.macro_f1_drop:.4f}</td></tr>"
        for row in perm.head(12).itertuples()
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NFL Feature Experiment Report</title>
  <style>
    body {{ margin: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #172026; background: #f7f9fb; }}
    header {{ padding: 48px 28px; background: #173b35; color: white; }}
    main {{ width: min(1120px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 56px; }}
    section {{ margin: 28px 0; background: white; border: 1px solid #d8e0e6; border-radius: 8px; padding: 22px; box-shadow: 0 12px 30px rgba(23,32,38,.08); }}
    h1 {{ margin: 0; font-size: clamp(2rem, 5vw, 4rem); line-height: 1; }}
    h2 {{ margin: 0 0 10px; }}
    p {{ color: #5a6872; }}
    table {{ width: 100%; border-collapse: collapse; font-size: .92rem; }}
    th, td {{ border-bottom: 1px solid #d8e0e6; padding: 10px 8px; text-align: left; }}
    th {{ font-size: .76rem; text-transform: uppercase; letter-spacing: .06em; color: #40515d; }}
    img {{ width: 100%; max-width: 1050px; border: 1px solid #d8e0e6; border-radius: 8px; background: white; }}
    code {{ background: #eef2f5; padding: 2px 5px; border-radius: 4px; }}
    .callout {{ border-left: 5px solid #13795b; background: #eefaf4; padding: 14px 16px; color: #234036; }}
  </style>
</head>
<body>
  <header>
    <h1>NFL Feature Experiment Report</h1>
    <p>Train seasons: {metadata["train_seasons"]}. Holdout season: {metadata["holdout_season"]}. Train rows: {metadata["train_rows"]:,}. Test rows: {metadata["test_rows"]:,}.</p>
  </header>
  <main>
    <section>
      <h2>Headline</h2>
      <div class="callout">The experiment compares the current random forest feature set, a no-yardage-bucket ablation, a tendency-feature variant, a staged random forest, and simple baselines on a true 2024 holdout.</div>
    </section>
    <section>
      <h2>Metric Summary</h2>
      <table><thead><tr><th>Experiment</th><th>Accuracy</th><th>Macro F1</th><th>Weighted F1</th><th>Pass F1</th><th>Run F1</th><th>Punt F1</th><th>FG F1</th></tr></thead><tbody>{result_rows}</tbody></table>
    </section>
    <section>
      <h2>Accuracy and F1</h2>
      <img src="{paths["metrics"].name}" alt="Accuracy and F1 bar chart">
    </section>
    <section>
      <h2>Removing Yardage Buckets</h2>
      <p>This isolates what happens when <code>short_yardage</code>, <code>medium_yardage</code>, and <code>long_yardage</code> are removed while raw <code>ydstogo</code> remains.</p>
      <img src="{paths["bucket_delta"].name}" alt="Yardage bucket ablation delta chart">
    </section>
    <section>
      <h2>Confusion Matrices</h2>
      <img src="{paths["confusion"].name}" alt="Confusion matrix comparison">
    </section>
    <section>
      <h2>Permutation Importance</h2>
      <p>Permutation importance measures how much macro F1 drops when one feature is shuffled in the holdout set.</p>
      <table><thead><tr><th>Feature</th><th>Macro F1 Drop</th></tr></thead><tbody>{perm_rows}</tbody></table>
      <img src="{paths["permutation"].name}" alt="Permutation importance chart">
    </section>
    <section>
      <h2>Stored Inference Feature Verification</h2>
      <p>The experiment recomputed these features from raw columns. This table shows what is currently stored in the SQLite DB before code fixes/backfill.</p>
      <table><thead><tr><th>Feature</th><th>Mismatches</th><th>Mismatch Rate</th><th>Stored Unique Sample</th></tr></thead><tbody>{verify_rows}</tbody></table>
    </section>
  </main>
</body>
</html>
"""
    path = OUT_DIR / "feature_experiment_report.html"
    path.write_text(html)
    return path


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = add_rolling_tendency_features(recompute_features(load_data()))
    verification = verify_stored_features(df)
    verification.to_csv(OUT_DIR / "stored_feature_verification.csv", index=False)

    train_df = df[df["season"] < HOLDOUT_SEASON].copy()
    test_df = df[df["season"] == HOLDOUT_SEASON].copy()
    train_df, test_df = add_tendency_features(train_df, test_df)

    results, predictions = run_experiments(train_df, test_df)
    results.to_csv(OUT_DIR / "experiment_results.csv", index=False)

    class_rows = []
    team_rows = []
    for name, pred in predictions.items():
        report = classification_report(test_df["play_type"], pred, labels=LABELS, output_dict=True, zero_division=0)
        for label in LABELS:
            class_rows.append({"experiment": name, "class": label, **report[label]})
        team_rows.extend(score_predictions_by_team(name, test_df, pred))
    pd.DataFrame(class_rows).to_csv(OUT_DIR / "per_class_results.csv", index=False)
    pd.DataFrame(team_rows).to_csv(OUT_DIR / "per_team_results.csv", index=False)

    for name, pred in predictions.items():
        cm = confusion_matrix(test_df["play_type"], pred, labels=LABELS)
        pd.DataFrame(cm, index=LABELS, columns=LABELS).to_csv(
            OUT_DIR / f"confusion_{name.lower().replace(' ', '_')}.csv"
        )

    print("Running permutation importance for current RF feature set...", flush=True)
    perm = permutation_importance_by_team(train_df, test_df, BASE_FEATURES)
    perm.to_csv(OUT_DIR / "permutation_importance.csv", index=False)

    paths = {
        "metrics": plot_metric_bars(results),
        "bucket_delta": plot_bucket_delta(results),
        "confusion": plot_confusions(predictions, test_df["play_type"]),
        "permutation": plot_permutation(perm),
    }

    metadata = {
        "db_path": str(DB_PATH),
        "train_seasons": f"{int(train_df['season'].min())}-{int(train_df['season'].max())}",
        "holdout_season": HOLDOUT_SEASON,
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "target_distribution_train": train_df["play_type"].value_counts().to_dict(),
        "target_distribution_test": test_df["play_type"].value_counts().to_dict(),
        "features_baseline": BASE_FEATURES,
        "features_no_bucket": [f for f in BASE_FEATURES if f not in BUCKET_FEATURES],
        "features_tendency": TENDENCY_FEATURES,
        "features_rolling_tendency": ROLLING_TENDENCY_FEATURES,
    }
    (OUT_DIR / "experiment_metadata.json").write_text(json.dumps(metadata, indent=2))
    report_path = write_html_report(results, verification, perm, paths, metadata)

    print("\nResults:")
    print(results.to_string(index=False))
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
