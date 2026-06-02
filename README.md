# NFL Play Predictor

A full-stack web application that predicts NFL play types before the snap:

- pass
- run
- punt
- field goal

Built with Django, React, and scikit-learn, the app uses team-specific staged Random Forest models trained on NFL play-by-play data from 2020 through 2025. Users can select a season, game, team, and historical play, then compare the model prediction against what actually happened.

---

## Features

- Play type prediction for historical NFL snaps.
- Team-specific models trained separately for each possession team.
- Staged modeling approach: first separates offense from special teams, then predicts the final play type.
- Pre-snap feature engineering using down, distance, yard line, score differential, time remaining, red zone, clock pressure, formation, and timeout context.
- Interactive React UI for selecting seasons, games, teams, and plays.
- Django REST API serving season, game, team, play, and prediction data.
- 2020-2025 play data available in the local app database.

---

## Tech Stack

**Frontend:** React, CSS, Webpack  
**Backend:** Django, Django REST Framework  
**Machine Learning:** Python, scikit-learn, pandas, joblib  
**Data:** nflverse/nflfastR play-by-play data from 2020-2025  

---

## Model Approach

The app uses team-specific staged Random Forest models.

The staged model works in two steps:

1. Decide whether the play is an offensive play or a special teams play.
2. Use the matching second-stage model:
   - offense model predicts `pass` or `run`
   - special teams model predicts `punt` or `field_goal`

This keeps the model from treating all four play types as one flat decision when the football decision is naturally split into two groups.

The web app shows the final prediction, model confidence, actual result, and whether the prediction matched.

---

## Model Performance

Recent holdout experiments compared several approaches:

- current Random Forest feature set
- Random Forest without redundant yardage bucket features
- Random Forest with broad tendency features
- Random Forest with rolling tendency features
- staged Random Forest models
- simple logistic baseline
- dummy baseline

The staged Random Forest with the current feature set performed best in the experiment, with about:

- **72.8% accuracy**
- **0.823 macro F1**

Removing redundant yardage bucket features was mostly neutral, while tendency features did not improve accuracy in the tested setup.

---

## Project Structure

```text
NflPbpPredictor/
├── download_pbp.py
├── clean_combine_pbp.py
├── model_training.py
├── requirements.txt
├── nflpredictor/
│   ├── manage.py
│   ├── db.sqlite3
│   ├── package.json
│   ├── webpack.config.js
│   ├── assets/
│   ├── core/
│   ├── saved_team_models/
│   └── static/
└── outputs/
```

---

## Setup

Install Python dependencies from the repo root:

```bash
pip install -r requirements.txt
```

If your system Python is externally managed, create a virtual environment first:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install frontend dependencies from the Django project directory:

```bash
cd nflpredictor
npm install
```

---

## Running The App

Run Django from the nested project directory:

```bash
cd nflpredictor
python manage.py migrate
python manage.py runserver
```

In another terminal, build or watch the frontend bundle:

```bash
cd nflpredictor
npm run dev
```

For a one-time production build:

```bash
cd nflpredictor
npm run build
```

---

## Deployment And URL

The deployed demo is configured for Northflank from the branch:

```text
nflpredictor/render-free-deploy
```

At the moment, `main` and `nflpredictor/render-free-deploy` are intentionally
kept identical so the resume/demo code, deployment branch, and GitHub
contribution history stay aligned.

Northflank provides a generated `*.code.run` URL. That generated URL cannot be
renamed to a plain display name like `NFL PBP Predictor`, because public URLs
cannot contain spaces and Northflank-generated URLs follow Northflank's service
and project naming format.

If you want a cleaner public URL, use a custom domain or subdomain, for example:

```text
nfl-pbp-predictor.com
nfl-pbp-predictor.your-domain.com
playcall.your-domain.com
```

After adding a custom domain in Northflank, point the DNS record to the service
port and add the custom hostname to `ALLOWED_HOSTS` if needed. See
`deploy/northflank/README.md` for the Northflank deployment settings.

---

## Testing

Run backend tests:

```bash
cd nflpredictor
python manage.py test
```

Run Django system checks:

```bash
cd nflpredictor
python manage.py check
```

Check frontend dependencies:

```bash
cd nflpredictor
npm audit --omit=dev
```

---

## Data Refresh

The current Django database includes seasons 2020 through 2025.

The data flow is:

1. Download nflverse play-by-play CSVs.
2. Clean the data to keep valid play types:
   - pass
   - run
   - punt
   - field_goal
3. Combine seasons into `combined_pbp_2020_2025_forest.csv`.
4. Train team-specific model artifacts.
5. Refresh the Django database with:

```bash
cd nflpredictor
python manage.py seed --mode refresh
```

The seed command clears and rebuilds the app data, so only run it when you intend to refresh the local database.

---

## Model Artifacts

Saved models live in:

```text
nflpredictor/saved_team_models/
```

Each team has flat model artifacts and staged model artifacts. The app uses staged models when all staged files exist for the selected team.

---

## Future Improvements

- Add real-time or upcoming-game prediction workflows.
- Improve calibration of confidence percentages.
- Compare staged Random Forests against additional model families.
- Add more robust frontend tests.
- Improve bundle size through code splitting.
- Add richer model evaluation pages directly inside the web app.
