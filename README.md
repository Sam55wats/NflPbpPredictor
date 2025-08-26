# NFL Play Predictor

A full-stack web application that predicts NFL play types (pass, run, punt, field goal) **before the snap** using team-specific machine learning models.  

Built with **Django, React, and scikit-learn**, the app achieves **70%–78% accuracy per team** on 2020–2024 NFL play-by-play data. Users can interactively explore games, view situational contexts, and compare model predictions against actual outcomes.  

---

## Features
- **Play Type Prediction:** Inference of past NFL plays (pass, run, punt, field goal).  
- **Team-Specific Models:** Random Forest classifiers trained on each team’s historical tendencies.  
- **Feature Engineering:** 20+ pre-snap features including down, distance, formation, score differential, timeout pressure, and red zone indicators.  
- **Interactive UI:** Select games and plays, view model predictions, and compare against actual results.  
- **REST API Backend:** Django-powered API serving ML predictions to a React frontend.

---

## Tech Stack
**Frontend:** React, CSS  
**Backend:** Django, Django REST Framework  
**Machine Learning:** Python, scikit-learn, Pandas  
**Data:** NFL play-by-play data (2020–2024) via [nflfastR](https://www.nflfastr.com/) and participation reports  

---

## Model Performance
- Accuracy per team ranges from **70%–78%**  
- Random Forest models with **hyperparameter tuning via RandomizedSearchCV**  

---

## Project Structure
NflPbpPredictor/
│── clean_combine_pbp.py # Cleans and merges play-by-play + participation data  
│── download_pbp.py # Downloads raw play-by-play data  
│── model_training.py # Trains Random Forest models per team  
│── db.sqlite3 # Local database for Django  
│── manage.py # Django project manager  
│── webpack.config.js # Webpack config for frontend  
│── package.json # Frontend dependencies  
│── package-lock.json  
│── .gitignore  
│── README.md  
│  
├── nflpredictor/ # Django app (backend logic, REST API, templates)  
├── saved_team_models/ # Serialized Random Forest models per team  
├── static/ # Static files (JS/CSS bundles)  
├── assets/ # Frontend assets  
├── core/ # Django core project config  

