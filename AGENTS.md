# AGENTS.md

## Project Overview

This repository is an NFL play-by-play prediction side project. It combines a Django + Django REST Framework backend, a React/Webpack frontend, and scikit-learn random forest models to predict pre-snap NFL play type:

- `pass`
- `run`
- `punt`
- `field_goal`

The app lets a user select a season, game, team, and historical play, then compares the model prediction with the actual play type. Models are team-specific and stored as `.joblib` artifacts.

## Repository Layout

- `README.md` - high-level project description and setup notes.
- `download_pbp.py` - downloads nflverse/nflfastR play-by-play CSVs into `nfl_pbp_csvs/`.
- `clean_combine_pbp.py` - filters downloaded CSVs to valid play types and combines seasons into one CSV.
- `model_training.py` - trains one random forest classifier per offensive team and saves models plus feature-name lists.
- `requirements.txt` - Python ML/data dependencies used by the root scripts.
- `nflpredictor/` - Django project root.
- `nflpredictor/manage.py` - Django management entry point.
- `nflpredictor/core/` - main Django app with models, serializers, views, URLs, templates, migrations, and seed command.
- `nflpredictor/assets/` - React source files and CSS.
- `nflpredictor/static/index-bundle.jsx` - Webpack output loaded by Django templates.
- `nflpredictor/saved_team_models/` - checked-in per-team random forest and feature-name `.joblib` files used by inference.

There are two SQLite files in the repo: `db.sqlite3` at the root and `nflpredictor/db.sqlite3`. Django settings use `nflpredictor/db.sqlite3` because `BASE_DIR` is the nested `nflpredictor/` directory.

## Backend

The Django app lives under `nflpredictor/core`.

Main models:

- `Season`: unique NFL season year.
- `Team`: team abbreviation and display name.
- `Game`: season, week, home team, away team.
- `Play`: historical play record with pre-snap features and actual `play_type`.

Main API routes are defined in `nflpredictor/core/urls.py`:

- `GET /api/season/` - list seasons.
- `GET /api/game/?season_id=<id>` - list games for a season.
- `GET /api/teams/?game_id=<id>` - return home and away teams for a game.
- `GET /api/plays/?game_id=<id>&team_id=<id>` - list plays where the selected team is the possession team.
- `GET /api/predict_play/?play_id=<id>` - load the selected team's model and return `{ prediction, actual }`.

`predict_play` in `nflpredictor/core/views.py` reconstructs the same feature set used during training, one-hot encodes `posteam_type` and `defteam`, then reindexes the inference dataframe against the saved feature-name list before calling the saved model.

Important: model paths in `predict_play` are relative paths like `saved_team_models/KC_rf_model.joblib`. This works when the Django server is launched from the nested `nflpredictor/` directory, where `saved_team_models/` exists.

## Frontend

React source is in `nflpredictor/assets`.

- `App.js` powers the home flow: select season, game, team, then navigate to `/analysis/?season=...&game=...&team=...`.
- `Analysis.js` reads those query params, fetches context and plays, then calls `/api/predict_play/` when a play is selected.
- `index.jsx` mounts either `App` or `Analysis` based on whether the current template has `root-home` or `root-analysis`.
- `styles.css` and `analysis.css` hold page styling.

The templates `nflpredictor/core/templates/home.html` and `analysis.html` load Bootstrap from a CDN and load the built bundle from Django static files.

Webpack config is `nflpredictor/webpack.config.js`. The bundle output is `nflpredictor/static/index-bundle.jsx`.

## Data and Model Flow

Typical offline workflow:

1. Run `download_pbp.py` to download play-by-play CSVs from nflverse releases.
2. Use `CleanCombinePBP.clean_data(...)` to keep non-null play types in `["pass", "run", "punt", "field_goal"]` and exclude two-point attempts.
3. Use `CleanCombinePBP.combine_cleaned_data(...)` to produce a combined CSV such as `combined_pbp_2024_forest.csv`.
4. Run `model_training.py` to:
   - add engineered features such as `is_losing`, yardage buckets, `clock_pressure`, `red_zone`, and `late_game`;
   - train a separate `RandomForestClassifier` for each `posteam`;
   - save `<TEAM>_rf_model.joblib`;
   - save `<TEAM>_feature_names.joblib`.
5. Seed the Django database from the combined CSV with `python manage.py seed --mode refresh`.

The seed command currently has a hard-coded absolute CSV path:

```python
csv_path = '/Users/samuelkim/NflPbpPredictor/combined_pbp_2024_forest.csv'
```

Be careful changing this because local data files may not be committed.

## Development Commands

Run backend commands from the nested Django directory:

```bash
cd nflpredictor
python manage.py migrate
python manage.py runserver
```

Run frontend build/watch from the nested Django directory:

```bash
cd nflpredictor
npm install
npm run dev
```

Run Django tests from the nested Django directory:

```bash
cd nflpredictor
python manage.py test
```

Install Python dependencies from the repo root:

```bash
pip install -r requirements.txt
```

Note: `requirements.txt` currently lists data/model dependencies but does not list Django or Django REST Framework, even though the web app requires them.

## Agent Guidance

- Preserve the distinction between the repo root and the nested Django root. Most web app commands should run from `nflpredictor/`.
- Prefer adding or updating focused tests in `nflpredictor/core/tests.py` when changing API behavior, model fields, serializers, or prediction logic.
- Keep the training feature list in `model_training.py` and the inference feature construction in `nflpredictor/core/views.py` synchronized. Any mismatch can silently degrade predictions or create missing-column bugs.
- Keep saved feature-name files synchronized with saved models. Inference depends on both artifacts for each team.
- Avoid retraining models unless the user explicitly asks. Training may require large local CSVs that are not present in the repository.
- Do not assume root-level generated data files such as `combined_pbp_2024_forest.csv`, `nfl_pbp_csvs/`, or cleaned CSV directories are available.
- Be cautious with `seed.py`: it clears and recreates database data in `refresh` mode, and `clear` deletes all `Play`, `Game`, `Team`, and `Season` records.
- Avoid committing `.DS_Store`, SQLite churn, generated bundles, or regenerated `.joblib` files unless the user specifically wants those artifacts updated.
- If changing frontend code, run or ask the user to run `npm run dev` so `nflpredictor/static/index-bundle.jsx` reflects the source changes.
- If changing model paths, prefer using `settings.BASE_DIR` to make path handling independent of the shell working directory.

## Known Rough Edges

- `TEAM_ABBR` in `views.py` is currently unused.
- `seed.py` does not populate every engineered `Play` field used by inference, including `posteam_type`, `defteam`, `is_losing`, yardage buckets, `quarter_half`, `clock_pressure`, `red_zone`, and `season`. Defaults may be used unless migrations/database data already contain values.
- `seed.py` maps `"LA"` to the Chargers and `"LAR"` to the Rams, while saved model filenames include `LA_*`, which may require care when interpreting Rams/Chargers abbreviations.
- `download_pbp.py` performs downloads at import/run time because it calls `download_pbp_csvs(BASE_URL, DIRECTORY)` at module bottom.
- There is no dedicated frontend test setup.
