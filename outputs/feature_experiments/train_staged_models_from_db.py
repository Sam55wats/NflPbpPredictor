import json
import shutil
import sqlite3
import time
import warnings
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier


warnings.filterwarnings("ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nflpredictor" / "db.sqlite3"
MODEL_DIR = ROOT / "nflpredictor" / "saved_team_models"
BACKUP_DIR = MODEL_DIR / "backup_before_staged_training"
METADATA_PATH = ROOT / "outputs" / "feature_experiments" / "staged_training_metadata.json"
RANDOM_STATE = 42

OFFENSE_PLAY_TYPES = {"pass", "run"}
SPECIAL_TEAMS_PLAY_TYPES = {"punt", "field_goal"}

FEATURES = [
    "down",
    "ydstogo",
    "yardline_100",
    "qtr",
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


def load_data():
    query = """
        SELECT
            p.down,
            p.ydstogo,
            p.yardline_100,
            p.quarter AS qtr,
            p.game_seconds_remaining,
            p.score_differential,
            p.posteam_type,
            p.defteam,
            t.team_abbr AS posteam,
            p.is_losing,
            p.late_game,
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
    return df


def prepare_team_matrix(df_team):
    X = df_team[FEATURES].copy()
    for col in BOOL_FEATURES:
        X[col] = X[col].fillna(False).astype(int)
    numeric_cols = X.columns.difference(["posteam_type", "defteam"])
    X[numeric_cols] = X[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    X[["posteam_type", "defteam"]] = X[["posteam_type", "defteam"]].fillna("unknown")
    X = pd.get_dummies(X, columns=["posteam_type", "defteam"], drop_first=True)
    return X.astype(float), df_team["play_type"].copy()


def random_forest():
    return RandomForestClassifier(
        n_estimators=180,
        max_depth=18,
        min_samples_leaf=4,
        min_samples_split=2,
        max_features="sqrt",
        class_weight="balanced_subsample",
        random_state=RANDOM_STATE,
        n_jobs=1,
    )


def backup_existing_artifacts(team):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in [
        "rf_model",
        "feature_names",
        "stage_model",
        "offense_model",
        "special_model",
        "staged_feature_names",
    ]:
        source = MODEL_DIR / f"{team}_{suffix}.joblib"
        dest = BACKUP_DIR / source.name
        if source.exists() and not dest.exists():
            shutil.copy2(source, dest)


def save_model(model, path):
    joblib.dump(model, path)


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data()
    rows = []
    started = time.perf_counter()

    print(f"Loaded {len(df):,} plays from {DB_PATH}")
    print(f"Saving models to {MODEL_DIR}")

    for team in sorted(df["posteam"].dropna().unique()):
        team_start = time.perf_counter()
        df_team = df[df["posteam"] == team].copy()
        X, y = prepare_team_matrix(df_team)
        feature_names = X.columns.tolist()
        backup_existing_artifacts(team)

        print(f"Training {team}: {len(df_team):,} plays, {len(feature_names)} encoded features", flush=True)

        flat_model = random_forest()
        flat_model.fit(X, y)
        save_model(flat_model, MODEL_DIR / f"{team}_rf_model.joblib")
        joblib.dump(feature_names, MODEL_DIR / f"{team}_feature_names.joblib")

        stage_y = y.apply(lambda play_type: "offense" if play_type in OFFENSE_PLAY_TYPES else "special")
        stage_model = random_forest()
        stage_model.fit(X, stage_y)
        save_model(stage_model, MODEL_DIR / f"{team}_stage_model.joblib")

        offense_mask = y.isin(OFFENSE_PLAY_TYPES)
        offense_model = random_forest()
        offense_model.fit(X[offense_mask], y[offense_mask])
        save_model(offense_model, MODEL_DIR / f"{team}_offense_model.joblib")

        special_mask = y.isin(SPECIAL_TEAMS_PLAY_TYPES)
        special_model = random_forest()
        special_model.fit(X[special_mask], y[special_mask])
        save_model(special_model, MODEL_DIR / f"{team}_special_model.joblib")
        joblib.dump(feature_names, MODEL_DIR / f"{team}_staged_feature_names.joblib")

        elapsed = time.perf_counter() - team_start
        row = {
            "team": team,
            "plays": int(len(df_team)),
            "encoded_features": int(len(feature_names)),
            "play_type_counts": y.value_counts().to_dict(),
            "seconds": elapsed,
        }
        rows.append(row)
        print(f"Saved {team} flat + staged models in {elapsed:.1f}s", flush=True)

    metadata = {
        "db_path": str(DB_PATH),
        "model_dir": str(MODEL_DIR),
        "backup_dir": str(BACKUP_DIR),
        "teams": rows,
        "total_seconds": time.perf_counter() - started,
        "features": FEATURES,
        "removed_features": ["short_yardage", "medium_yardage", "long_yardage"],
        "staged_artifacts": [
            "<TEAM>_stage_model.joblib",
            "<TEAM>_offense_model.joblib",
            "<TEAM>_special_model.joblib",
            "<TEAM>_staged_feature_names.joblib",
        ],
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))
    print(f"Training complete in {metadata['total_seconds']:.1f}s")
    print(f"Metadata: {METADATA_PATH}")


if __name__ == "__main__":
    main()
