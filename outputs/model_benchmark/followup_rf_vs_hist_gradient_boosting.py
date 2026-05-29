import io
import json
import sqlite3
import time
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nflpredictor" / "db.sqlite3"
OUT_DIR = ROOT / "outputs" / "model_benchmark"
RANDOM_STATE = 42
TRAIN_SEASONS = [2020, 2021, 2022, 2023]
TEST_SEASON = 2024
LABELS = ["pass", "run", "punt", "field_goal"]

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


def load_reconstructed_data():
    query = """
        SELECT
            p.game_id,
            offense.team_abbr AS posteam,
            home_team.team_abbr AS home_team,
            away_team.team_abbr AS away_team,
            seasons.year AS season,
            p.down,
            p.ydstogo,
            p.yardline_100,
            p.quarter AS qtr,
            p.game_seconds_remaining,
            p.score_differential,
            p.shotgun,
            p.no_huddle,
            p.goal_to_go,
            p.defteam_timeouts_remaining,
            p.posteam_timeouts_remaining,
            p.half_seconds_remaining,
            p.quarter_seconds_remaining,
            p.play_type
        FROM core_play p
        JOIN core_team offense ON offense.id = p.posteam_id
        JOIN core_game games ON games.id = p.game_id
        JOIN core_team home_team ON home_team.id = games.home_team_id
        JOIN core_team away_team ON away_team.id = games.away_team_id
        JOIN core_season seasons ON seasons.id = games.season_id
        WHERE p.play_type IN ('pass', 'run', 'punt', 'field_goal')
    """
    with sqlite3.connect(DB_PATH) as connection:
        df = pd.read_sql_query(query, connection)

    return df.assign(
        posteam_type=np.where(df["posteam"] == df["home_team"], "home", "away"),
        defteam=np.where(
            df["posteam"] == df["home_team"], df["away_team"], df["home_team"]
        ),
        is_losing=(df["score_differential"] < 0).astype(int),
        short_yardage=(df["ydstogo"] <= 3).astype(int),
        medium_yardage=((df["ydstogo"] > 3) & (df["ydstogo"] <= 7)).astype(int),
        long_yardage=(df["ydstogo"] > 7).astype(int),
        quarter_half=(df["qtr"] <= 2).astype(int),
        clock_pressure=(df["half_seconds_remaining"] <= 120).astype(int),
        red_zone=(df["yardline_100"] <= 20).astype(int),
        late_game=(df["game_seconds_remaining"] <= 120).astype(int),
    )


def encode_team_split(train_df, test_df):
    train_x = train_df[FEATURES].copy()
    test_x = test_df[FEATURES].copy()
    categorical = ["posteam_type", "defteam"]
    numeric = [feature for feature in FEATURES if feature not in categorical]

    for frame in (train_x, test_x):
        frame.loc[:, numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce").fillna(0)
        frame.loc[:, categorical] = frame[categorical].fillna("unknown")

    train_x = pd.get_dummies(train_x, columns=categorical, drop_first=True)
    test_x = pd.get_dummies(test_x, columns=categorical, drop_first=True)
    test_x = test_x.reindex(columns=train_x.columns, fill_value=0)
    return train_x.astype(float), test_x.astype(float)


def model_specs():
    return {
        "Random Forest": RandomForestClassifier(
            n_estimators=180,
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
        "Hist Gradient Boosting Balanced": HistGradientBoostingClassifier(
            max_iter=180,
            learning_rate=0.08,
            l2_regularization=0.05,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
    }


def serialized_size_kb(model):
    buffer = io.BytesIO()
    joblib.dump(model, buffer, compress=3)
    return len(buffer.getvalue()) / 1024


def evaluate_per_team(df):
    rows = []
    predictions = {model_name: {"actual": [], "predicted": []} for model_name in model_specs()}
    train_df = df[df["season"].isin(TRAIN_SEASONS)]
    test_df = df[df["season"] == TEST_SEASON]

    for team in sorted(df["posteam"].unique()):
        team_train = train_df[train_df["posteam"] == team]
        team_test = test_df[test_df["posteam"] == team]
        train_x, test_x = encode_team_split(team_train, team_test)
        train_y = team_train["play_type"]
        test_y = team_test["play_type"]

        for model_name, model in model_specs().items():
            fit_start = time.perf_counter()
            model.fit(train_x, train_y)
            fit_seconds = time.perf_counter() - fit_start

            predict_start = time.perf_counter()
            predicted = model.predict(test_x)
            predict_seconds = time.perf_counter() - predict_start

            predictions[model_name]["actual"].extend(test_y.tolist())
            predictions[model_name]["predicted"].extend(predicted.tolist())
            rows.append(
                {
                    "team": team,
                    "model": model_name,
                    "train_rows": len(team_train),
                    "test_rows": len(team_test),
                    "feature_count": train_x.shape[1],
                    "accuracy": accuracy_score(test_y, predicted),
                    "macro_f1": f1_score(test_y, predicted, labels=LABELS, average="macro"),
                    "weighted_f1": f1_score(test_y, predicted, labels=LABELS, average="weighted"),
                    "fit_seconds": fit_seconds,
                    "predict_seconds": predict_seconds,
                    "artifact_size_kb": serialized_size_kb(model),
                }
            )
        print(f"Completed {team}", flush=True)
    return pd.DataFrame(rows), predictions


def aggregate_results(results, predictions):
    rows = []
    class_rows = []
    matrices = {}
    for model_name, scored in predictions.items():
        actual = scored["actual"]
        predicted = scored["predicted"]
        model_rows = results[results["model"] == model_name]
        report = classification_report(
            actual, predicted, labels=LABELS, output_dict=True, zero_division=0
        )
        rows.append(
            {
                "model": model_name,
                "accuracy": accuracy_score(actual, predicted),
                "macro_f1": f1_score(actual, predicted, labels=LABELS, average="macro"),
                "weighted_f1": f1_score(actual, predicted, labels=LABELS, average="weighted"),
                "fit_seconds_total": model_rows["fit_seconds"].sum(),
                "predict_seconds_total": model_rows["predict_seconds"].sum(),
                "artifact_size_mb_total": model_rows["artifact_size_kb"].sum() / 1024,
                "team_macro_f1_mean": model_rows["macro_f1"].mean(),
                "team_macro_f1_median": model_rows["macro_f1"].median(),
            }
        )
        for label in LABELS:
            class_rows.append(
                {
                    "model": model_name,
                    "play_type": label,
                    "precision": report[label]["precision"],
                    "recall": report[label]["recall"],
                    "f1": report[label]["f1-score"],
                    "support": int(report[label]["support"]),
                }
            )
        matrices[model_name] = confusion_matrix(actual, predicted, labels=LABELS, normalize="true")
    return pd.DataFrame(rows), pd.DataFrame(class_rows), matrices


def plot_comparison(results, aggregate, matrices):
    paired = results.pivot(index="team", columns="model", values="macro_f1")
    paired = paired.assign(
        delta_hgb_minus_rf=paired["Hist Gradient Boosting"] - paired["Random Forest"]
    )
    paired = paired.sort_values("delta_hgb_minus_rf")

    palette = {
        "Random Forest": "#E15759",
        "Hist Gradient Boosting": "#4E79A7",
        "Hist Gradient Boosting Balanced": "#59A14F",
    }
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(17, 13))

    metric_names = ["accuracy", "macro_f1"]
    positions = np.arange(len(metric_names))
    bar_width = 0.24
    offsets = np.linspace(-bar_width, bar_width, len(palette))
    for offset, model_name in zip(offsets, palette):
        values = aggregate.loc[aggregate["model"] == model_name, metric_names].iloc[0]
        axes[0, 0].bar(
            positions + offset,
            values,
            width=bar_width,
            label=model_name,
            color=palette[model_name],
        )
    axes[0, 0].set_title("2024 Holdout: Overall Predictive Quality")
    axes[0, 0].set_ylim(0, 1)
    axes[0, 0].set_xticks(positions, ["Accuracy", "Macro F1"])
    axes[0, 0].set_xlabel("")
    axes[0, 0].set_ylabel("Score")
    axes[0, 0].legend()

    colors = np.where(paired["delta_hgb_minus_rf"] >= 0, "#4E79A7", "#E15759")
    axes[0, 1].barh(paired.index, paired["delta_hgb_minus_rf"], color=colors)
    axes[0, 1].axvline(0, color="#222222", linewidth=1)
    axes[0, 1].set_title("Per-Team Macro F1 Change")
    axes[0, 1].set_xlabel("Hist Gradient Boosting minus Random Forest")
    axes[0, 1].set_ylabel("")

    for axis, model_name in zip(axes[1], ["Random Forest", "Hist Gradient Boosting"]):
        matrix = matrices[model_name]
        heatmap = axis.imshow(
            matrix,
            cmap="Blues" if model_name == "Hist Gradient Boosting" else "Reds",
            vmin=0,
            vmax=1,
        )
        for row in range(matrix.shape[0]):
            for col in range(matrix.shape[1]):
                axis.text(col, row, f"{matrix[row, col]:.2f}", ha="center", va="center")
        axis.set_xticks(range(len(LABELS)), LABELS)
        axis.set_yticks(range(len(LABELS)), LABELS)
        fig.colorbar(heatmap, ax=axis, fraction=0.046, pad=0.04)
        axis.set_title(f"{model_name}: Recall-Normalized Confusion")
        axis.set_xlabel("Predicted")
        axis.set_ylabel("Actual")

    fig.suptitle(
        "Per-Team NFL Play-Type Model Follow-up: Train 2020-2023, Test 2024",
        fontsize=17,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    plot_path = OUT_DIR / "rf_vs_hist_gradient_boosting_2024_holdout.png"
    fig.savefig(plot_path, dpi=170)
    plt.close(fig)
    return plot_path, paired


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_reconstructed_data()
    results, predictions = evaluate_per_team(df)
    aggregate, by_class, matrices = aggregate_results(results, predictions)
    plot_path, paired = plot_comparison(results, aggregate, matrices)

    detail_path = OUT_DIR / "rf_vs_hist_gradient_boosting_by_team.csv"
    aggregate_path = OUT_DIR / "rf_vs_hist_gradient_boosting_summary.csv"
    class_path = OUT_DIR / "rf_vs_hist_gradient_boosting_by_class.csv"
    paired_path = OUT_DIR / "rf_vs_hist_gradient_boosting_team_deltas.csv"
    metadata_path = OUT_DIR / "rf_vs_hist_gradient_boosting_metadata.json"

    results.to_csv(detail_path, index=False)
    aggregate.to_csv(aggregate_path, index=False)
    by_class.to_csv(class_path, index=False)
    paired.to_csv(paired_path)
    metadata = {
        "data_source": str(DB_PATH),
        "evaluation": "fresh per-team models trained on seasons 2020-2023 and tested on season 2024",
        "feature_reconstruction": "posteam_type, defteam, season, and engineered flags reconstructed from game/play context because database Play defaults were not populated",
        "rows_total": int(len(df)),
        "train_rows": int(df[df["season"].isin(TRAIN_SEASONS)].shape[0]),
        "test_rows": int(df[df["season"] == TEST_SEASON].shape[0]),
        "teams": int(df["posteam"].nunique()),
        "train_seasons": TRAIN_SEASONS,
        "test_season": TEST_SEASON,
        "models": {
            "Random Forest": "180 estimators, max_depth=18, min_samples_leaf=4, class_weight=balanced",
            "Hist Gradient Boosting": "180 iterations, learning_rate=0.08, l2_regularization=0.05",
            "Hist Gradient Boosting Balanced": "same HGB settings with class_weight=balanced",
        },
        "outputs": {
            "summary_csv": str(aggregate_path),
            "by_team_csv": str(detail_path),
            "by_class_csv": str(class_path),
            "team_deltas_csv": str(paired_path),
            "plot": str(plot_path),
        },
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))

    print("\nAggregate results:")
    print(aggregate.to_string(index=False))
    print("\nResults by play type:")
    print(by_class.to_string(index=False))
    print(
        "\nTeam wins on macro F1 (unweighted HGB vs RF):",
        int((paired["delta_hgb_minus_rf"] > 0).sum()),
        "HGB /",
        int((paired["delta_hgb_minus_rf"] < 0).sum()),
        "RF /",
        int((paired["delta_hgb_minus_rf"] == 0).sum()),
        "ties",
    )
    print(f"\nSaved visualization: {plot_path}")


if __name__ == "__main__":
    main()
