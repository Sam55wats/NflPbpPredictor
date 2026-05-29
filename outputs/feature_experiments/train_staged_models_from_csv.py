import argparse
import json
import shutil
import time
import warnings
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier


warnings.filterwarnings("ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "nflpredictor" / "saved_team_models"
DEFAULT_CSV_PATH = ROOT / "combined_pbp_2020_2025_forest.csv"
DEFAULT_BACKUP_DIR = MODEL_DIR / "backup_before_nflverse_2020_2025_training"
METADATA_PATH = ROOT / "outputs" / "feature_experiments" / "staged_training_2020_2025_metadata.json"
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


def add_engineered_features(df):
    df = df.copy()
    df["is_losing"] = (df["score_differential"] < 0).astype(int)
    df["late_game"] = (df["game_seconds_remaining"] <= 120).astype(int)
    df["quarter_half"] = (df["qtr"] <= 2).astype(int)
    df["clock_pressure"] = (df["half_seconds_remaining"] <= 120).astype(int)
    df["red_zone"] = (df["yardline_100"] <= 20).astype(int)
    return df


def load_data(csv_path):
    usecols = sorted(
        set(
            FEATURES
            + [
                "posteam",
                "play_type",
                "home_team",
                "away_team",
                "week",
            ]
        )
        - {"is_losing", "late_game", "quarter_half", "clock_pressure", "red_zone"}
    )
    df = pd.read_csv(csv_path, usecols=usecols, low_memory=False)
    df = df[df["play_type"].isin(["pass", "run", "punt", "field_goal"])].copy()
    return add_engineered_features(df)


def prepare_team_matrix(df_team):
    X = df_team[FEATURES].copy()
    for col in BOOL_FEATURES:
        X[col] = X[col].fillna(False).astype(int)
    numeric_cols = X.columns.difference(["posteam_type", "defteam"])
    X[numeric_cols] = X[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    X[["posteam_type", "defteam"]] = X[["posteam_type", "defteam"]].fillna("unknown")
    X = pd.get_dummies(X, columns=["posteam_type", "defteam"], drop_first=True)
    return X.astype(float), df_team["play_type"].copy()


def backup_existing_artifacts(team, backup_dir):
    backup_dir.mkdir(parents=True, exist_ok=True)
    for suffix in [
        "rf_model",
        "feature_names",
        "stage_model",
        "offense_model",
        "special_model",
        "staged_feature_names",
    ]:
        source = MODEL_DIR / f"{team}_{suffix}.joblib"
        dest = backup_dir / source.name
        if source.exists() and not dest.exists():
            shutil.copy2(source, dest)


def save_team_models(team, X, y):
    flat_model = random_forest()
    flat_model.fit(X, y)
    joblib.dump(flat_model, MODEL_DIR / f"{team}_rf_model.joblib")
    joblib.dump(X.columns.tolist(), MODEL_DIR / f"{team}_feature_names.joblib")

    stage_y = y.apply(lambda play_type: "offense" if play_type in OFFENSE_PLAY_TYPES else "special")
    stage_model = random_forest()
    stage_model.fit(X, stage_y)
    joblib.dump(stage_model, MODEL_DIR / f"{team}_stage_model.joblib")

    offense_mask = y.isin(OFFENSE_PLAY_TYPES)
    offense_model = random_forest()
    offense_model.fit(X[offense_mask], y[offense_mask])
    joblib.dump(offense_model, MODEL_DIR / f"{team}_offense_model.joblib")

    special_mask = y.isin(SPECIAL_TEAMS_PLAY_TYPES)
    special_model = random_forest()
    special_model.fit(X[special_mask], y[special_mask])
    joblib.dump(special_model, MODEL_DIR / f"{team}_special_model.joblib")
    joblib.dump(X.columns.tolist(), MODEL_DIR / f"{team}_staged_feature_names.joblib")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    args = parser.parse_args()

    started = time.perf_counter()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data(args.csv)

    print(f"Loaded {len(df):,} plays from {args.csv}")
    print(f"Seasons: {int(df['season'].min())}-{int(df['season'].max())}")
    print(f"Saving models to {MODEL_DIR}")
    print(f"Backing up previous artifacts to {args.backup_dir}")

    rows = []
    for team in sorted(df["posteam"].dropna().unique()):
        team_start = time.perf_counter()
        df_team = df[df["posteam"] == team].copy()
        X, y = prepare_team_matrix(df_team)
        backup_existing_artifacts(team, args.backup_dir)
        print(f"Training {team}: {len(df_team):,} plays, {len(X.columns)} encoded features", flush=True)
        save_team_models(team, X, y)
        elapsed = time.perf_counter() - team_start
        rows.append(
            {
                "team": team,
                "plays": int(len(df_team)),
                "encoded_features": int(len(X.columns)),
                "play_type_counts": y.value_counts().to_dict(),
                "seconds": elapsed,
            }
        )
        print(f"Saved {team} flat + staged models in {elapsed:.1f}s", flush=True)

    metadata = {
        "csv_path": str(args.csv),
        "model_dir": str(MODEL_DIR),
        "backup_dir": str(args.backup_dir),
        "rows": int(len(df)),
        "season_counts": {str(k): int(v) for k, v in df.groupby("season").size().to_dict().items()},
        "teams": rows,
        "total_seconds": time.perf_counter() - started,
        "features": FEATURES,
        "removed_features": ["short_yardage", "medium_yardage", "long_yardage"],
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))
    print(f"Training complete in {metadata['total_seconds']:.1f}s")
    print(f"Metadata: {METADATA_PATH}")


if __name__ == "__main__":
    main()
