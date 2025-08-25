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
**Frontend:** React, TailwindCSS  
**Backend:** Django, Django REST Framework  
**Machine Learning:** Python, scikit-learn, Pandas
**Data:** NFL play-by-play data (2020–2024) via [nflfastR](https://www.nflfastr.com/) and participation reports  

---

