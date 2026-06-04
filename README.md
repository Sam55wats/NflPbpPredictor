# NFL PBP Predictor

NFL PBP Predictor is a Django and React web app that predicts pre-snap NFL play type for historical plays:

- `pass`
- `run`
- `punt`
- `field_goal`

The app uses team-specific scikit-learn Random Forest artifacts trained from nflverse/nflfastR play-by-play data. A user selects a season, game, team, and historical play, then the app compares the model prediction with the actual result.

## What The App Does

- Serves a Django REST API for seasons, games, teams, plays, and predictions.
- Uses a React/Webpack frontend for the selection and analysis flow.
- Loads checked-in per-team model artifacts from `nflpredictor/saved_team_models/`.
- Uses staged models when available:
  1. Classify the play as `offense` or `special`.
  2. Route to an offense model for `pass` vs `run`, or a special teams model for `punt` vs `field_goal`.
- Falls back to the older flat four-class Random Forest model if staged artifacts are missing.

Website/demo inference uses staged model artifacts trained on the available 2020-2025 data. Holdout experiment results are separate from the website models and are used to estimate generalization.

## Tech Stack

**Backend:** Django, Django REST Framework  
**Frontend:** React, Webpack, CSS  
**Machine learning:** scikit-learn, pandas, joblib  
**Data source:** nflverse/nflfastR play-by-play CSVs  
**Database:** SQLite for the local/demo Django app

## Repository Layout

```text
NflPbpPredictor/
├── README.md
├── requirements.txt
├── download_pbp.py
├── clean_combine_pbp.py
├── model_training.py
├── nflpredictor/
│   ├── manage.py
│   ├── db.sqlite3
│   ├── package.json
│   ├── webpack.config.js
│   ├── assets/
│   ├── core/
│   ├── saved_team_models/
│   └── static/
├── outputs/
│   ├── feature_experiments/
│   ├── feature_experiments_2025_holdout/
│   └── model_benchmark/
└── deploy/
```

The Django project root is the nested `nflpredictor/` directory. Django settings use `nflpredictor/db.sqlite3` at the repository root.

## Setup

Install Python dependencies from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install frontend dependencies from the nested Django project:

```bash
cd nflpredictor
npm install
```

## Running Locally

Run Django from the nested project directory:

```bash
cd nflpredictor
python3 manage.py migrate
python3 manage.py runserver
```

Build or watch the frontend bundle from the same nested directory:

```bash
cd nflpredictor
npm run dev
```

For a one-time production bundle:

```bash
cd nflpredictor
npm run build
```

## API Routes

- `GET /api/season/` lists seasons.
- `GET /api/game/?season_id=<id>` lists games for a season.
- `GET /api/teams/?game_id=<id>` returns the home and away teams for a game.
- `GET /api/plays/?game_id=<id>&team_id=<id>` lists plays where the selected team has possession.
- `GET /api/predict_play/?play_id=<id>` returns the model prediction, confidence, actual play type, and match result.

## Data And Models

The normal offline workflow is:

1. Download nflverse play-by-play CSVs with `download_pbp.py`.
2. Clean and combine valid play types with `clean_combine_pbp.py`.
3. Train per-team model artifacts.
4. Refresh the Django database:

```bash
cd nflpredictor
python3 manage.py seed --mode refresh
```

The seed command clears and rebuilds local app data. Generated raw and combined CSVs are intentionally ignored by Git because they are large local artifacts.

## Model Evaluation

Recent 2025 holdout experiments trained on 2020-2024 data and tested on 2025 data. The strongest raw accuracy came from the flat Random Forest current feature set:

| Experiment | Accuracy | Macro F1 |
| --- | ---: | ---: |
| Flat RF current feature set | 0.7335 | 0.8164 |
| Staged RF current features | 0.7317 | 0.8192 |
| Staged RF no buckets | 0.7329 | 0.8185 |

Accuracy is the share of correct predictions. Macro F1 averages class-level F1 scores equally, which matters because `pass` and `run` are much more common than `punt` and `field_goal`.

The staged model's hardest step is `pass` vs `run`. Its 2025 component evaluation showed strong offense/special routing and strong punt/field-goal separation, while the offense submodel was the main source of misses.

## Testing

Run backend tests:

```bash
cd nflpredictor
python3 manage.py test
```

Run Django checks:

```bash
cd nflpredictor
python3 manage.py check
```

Check frontend production dependencies:

```bash
cd nflpredictor
npm audit --omit=dev
```

## Deployment

The app includes deployment files for hosted demos:

- `Dockerfile`
- `build.sh`
- `requirements-render.txt`
- `deploy/northflank/`
- `deploy/oracle/`

The active deployment branch for the hosted demo is:

```text
nflpredictor/render-free-deploy
```

See `deploy/northflank/README.md` for Northflank settings.

## Notes

- The checked-in `nflpredictor/static/index-bundle.jsx` is the frontend bundle loaded by Django templates.
- `nflpredictor/saved_team_models/` contains required inference artifacts and should stay synchronized with feature names.
- Local interview guide pages and other private notes under `docs/` are ignored so they can exist locally without appearing on GitHub.
