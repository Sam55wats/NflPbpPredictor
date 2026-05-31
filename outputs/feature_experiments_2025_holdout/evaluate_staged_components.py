import json
import sqlite3
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score


warnings.filterwarnings("ignore", category=FutureWarning)

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nflpredictor" / "db.sqlite3"
OUT_DIR = ROOT / "outputs" / "feature_experiments_2025_holdout"
RANDOM_STATE = 42
HOLDOUT_SEASON = 2025
OFFENSE_TYPES = ["pass", "run"]
SPECIAL_TYPES = ["field_goal", "punt"]

FEATURES = [
    "down",
    "ydstogo",
    "yardline_100",
    "quarter",
    "game_seconds_remaining",
    "score_differential",
    "posteam_type",
    "defteam",
    "is_losing",
    "late_game",
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

BOOL_FEATURES = [
    "is_losing",
    "late_game",
    "clock_pressure",
    "red_zone",
    "shotgun",
    "no_huddle",
    "goal_to_go",
]


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
            t.team_abbr AS posteam,
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
        return pd.read_sql_query(query, conn)


def add_features(df):
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
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["is_losing"] = (df["score_differential"] < 0).astype(int)
    df["quarter_half"] = (df["quarter"] <= 2).astype(int)
    df["clock_pressure"] = (df["half_seconds_remaining"] <= 120).astype(int)
    df["red_zone"] = (df["yardline_100"] <= 20).astype(int)
    df["late_game"] = (df["game_seconds_remaining"] <= 120).astype(int)
    df["posteam_type"] = np.where(df["posteam"] == df["home_team"], "home", "away")
    df["defteam"] = np.where(df["posteam"] == df["home_team"], df["away_team"], df["home_team"])
    df["stage_label"] = np.where(df["play_type"].isin(OFFENSE_TYPES), "offense", "special")
    return df


def prepare_matrix(train_df, test_df):
    train_x = train_df[FEATURES].copy()
    test_x = test_df[FEATURES].copy()
    combined = pd.concat([train_x, test_x], axis=0, ignore_index=True)
    for col in BOOL_FEATURES:
        combined[col] = combined[col].fillna(False).astype(int)
    combined[["posteam_type", "defteam"]] = combined[["posteam_type", "defteam"]].fillna("unknown")
    numeric_cols = combined.columns.difference(["posteam_type", "defteam"])
    combined[numeric_cols] = combined[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    combined = pd.get_dummies(combined, columns=["posteam_type", "defteam"], drop_first=True).astype(float)
    return combined.iloc[: len(train_df)].copy(), combined.iloc[len(train_df) :].copy()


def metrics_row(component, team, y_true, y_pred, labels):
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)
    row = {
        "component": component,
        "team": team,
        "support": int(len(y_true)),
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0),
    }
    for label in labels:
        row[f"precision_{label}"] = report[label]["precision"]
        row[f"recall_{label}"] = report[label]["recall"]
        row[f"f1_{label}"] = report[label]["f1-score"]
    return row


def main():
    started = time.perf_counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = add_features(load_data())
    train_df = df[df["season"] < HOLDOUT_SEASON].copy()
    test_df = df[df["season"] == HOLDOUT_SEASON].copy()

    stage_parts = []
    offense_parts = []
    special_parts = []
    final_parts = []

    for team in sorted(test_df["posteam"].unique()):
        train_team = train_df[train_df["posteam"] == team].copy()
        test_team = test_df[test_df["posteam"] == team].copy()
        if train_team.empty or test_team.empty:
            continue

        x_train, x_test = prepare_matrix(train_team, test_team)
        stage_model = rf_model()
        stage_model.fit(x_train, train_team["stage_label"])
        stage_pred = pd.Series(stage_model.predict(x_test), index=test_team.index)
        stage_parts.append((team, test_team["stage_label"], stage_pred))

        final_pred = pd.Series(index=test_team.index, dtype=object)
        for component, classes, parts in [
            ("offense_submodel", OFFENSE_TYPES, offense_parts),
            ("special_submodel", SPECIAL_TYPES, special_parts),
        ]:
            train_sub = train_team[train_team["play_type"].isin(classes)].copy()
            test_sub = test_team[test_team["play_type"].isin(classes)].copy()
            if train_sub.empty or test_sub.empty:
                continue
            x_sub_train, x_sub_test = prepare_matrix(train_sub, test_sub)
            sub_model = rf_model()
            sub_model.fit(x_sub_train, train_sub["play_type"])
            sub_pred = pd.Series(sub_model.predict(x_sub_test), index=test_sub.index)
            parts.append((team, test_sub["play_type"], sub_pred))

            routed_index = test_team.index[stage_pred == ("offense" if component == "offense_submodel" else "special")]
            if len(routed_index):
                _, x_routed = prepare_matrix(train_sub, test_team.loc[routed_index])
                final_pred.loc[routed_index] = sub_model.predict(x_routed)

        final_pred = final_pred.fillna(train_team["play_type"].mode().iloc[0])
        final_parts.append((team, test_team["play_type"], final_pred))

    rows = []
    confusion_outputs = []
    for component, parts, labels in [
        ("stage_offense_vs_special", stage_parts, ["offense", "special"]),
        ("offense_submodel_pass_vs_run", offense_parts, OFFENSE_TYPES),
        ("special_submodel_field_goal_vs_punt", special_parts, SPECIAL_TYPES),
        ("full_staged_prediction", final_parts, ["field_goal", "pass", "punt", "run"]),
    ]:
        all_true = pd.concat([p[1] for p in parts]).sort_index()
        all_pred = pd.concat([p[2] for p in parts]).sort_index()
        rows.append(metrics_row(component, "ALL", all_true, all_pred, labels))
        cm = pd.DataFrame(confusion_matrix(all_true, all_pred, labels=labels), index=labels, columns=labels)
        cm.to_csv(OUT_DIR / f"staged_component_confusion_{component}.csv")
        confusion_outputs.append(str(OUT_DIR / f"staged_component_confusion_{component}.csv"))
        for team, y_true, y_pred in parts:
            rows.append(metrics_row(component, team, y_true, y_pred, labels))

    metrics = pd.DataFrame(rows)
    metrics.to_csv(OUT_DIR / "staged_component_metrics.csv", index=False)
    metadata = {
        "train_seasons": f"{int(train_df['season'].min())}-{int(train_df['season'].max())}",
        "holdout_season": HOLDOUT_SEASON,
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "metrics_csv": str(OUT_DIR / "staged_component_metrics.csv"),
        "confusion_csvs": confusion_outputs,
        "seconds": time.perf_counter() - started,
    }
    (OUT_DIR / "staged_component_metadata.json").write_text(json.dumps(metadata, indent=2))
    print(metrics[metrics["team"] == "ALL"].to_string(index=False))
    print(f"Saved: {OUT_DIR / 'staged_component_metrics.csv'}")


if __name__ == "__main__":
    main()
