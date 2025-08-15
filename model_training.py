import pandas as pd
import pdb
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, RandomizedSearchCV, cross_validate
from sklearn.metrics import accuracy_score
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from clean_combine_pbp import CleanCombinePBP
from scipy.stats import randint
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import joblib
import os

from sklearn.tree import export_graphviz
from IPython.display import Image
import graphviz

MODEL_DIR = "saved_team_models"
os.makedirs("saved_team_models", exist_ok=True)

valid_play_types = ["pass", "run", "punt", "field_goal"]
#cleaner = CleanCombinePBP()
#cleaner.clean_data(valid_play_types, "cleaned_pbp_forest_part")
#cleaner.combine_cleaned_data("cleaned_pbp_forest_part", "combined_pbp_2024_forest.csv")

df = pd.read_csv("combined_pbp_2024_forest.csv", low_memory=False)

df["is_losing"] = (df["score_differential"] < 0).astype(int)
df["short_yardage"] = (df["ydstogo"] <= 3).astype(int)
df["medium_yardage"] = ((df["ydstogo"] > 3) & (df["ydstogo"] <= 7)).astype(int)
df["long_yardage"] = (df["ydstogo"] > 7).astype(int)
df["quarter_half"] = (df["qtr"] <= 2).astype(int)  # 1st half = 1, 2nd half = 0
df["clock_pressure"] = (df["half_seconds_remaining"] <= 120).astype(int)  # 2 minutes or less in the half
df["red_zone"] = (df["yardline_100"] <= 20).astype(int)  # within 20 yards of the end zone
df["late_game"] = (df["game_seconds_remaining"] <= 120).astype(int)
df["team_short_pass_rate"] = df.groupby("posteam")["short_yardage"].transform(lambda x: x.mean() if x.sum() > 0 else 0)
df["team_pass_rate"] = df.groupby("posteam")["play_type"].transform(lambda x: (x == "pass").mean())


features = ["down", "ydstogo", "yardline_100", "qtr", "game_seconds_remaining", 
            "score_differential", "posteam_type", "defteam", "is_losing", 
            "short_yardage", "late_game", "medium_yardage", "long_yardage", "quarter_half", 
            "clock_pressure", "red_zone", "season", "shotgun", "no_huddle", "goal_to_go", 
            "defteam_timeouts_remaining", "posteam_timeouts_remaining", "half_seconds_remaining",
            "quarter_seconds_remaining"]

target = "play_type"
team_models = {}


for team in df["posteam"].unique():
    df_team = df[df["posteam"] == team]

    X = df_team[features]
    y = df_team[target]

    X = pd.get_dummies(X, columns=["posteam_type", "defteam"], drop_first=True) # Convert categorical variables to dummy variables

    feature_names = X.columns.tolist()
    feature_path = os.path.join(MODEL_DIR, f"{team}_feature_names.joblib")
    joblib.dump(feature_names, feature_path)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    param_dist = {
    "n_estimators": randint(50, 200),
    "max_depth": randint(5, 20),
    "min_samples_split": randint(2, 10),
    "min_samples_leaf": randint(1, 10),
    "max_features": ["sqrt", "log2"]
    }

    base_model = RandomForestClassifier(random_state=42, class_weight="balanced")

    search = RandomizedSearchCV(
        base_model,
        param_distributions=param_dist,
        n_iter=25,            
        cv=2,                 
        scoring='accuracy',
        n_jobs=-1,           
        verbose=0,
        random_state=42
    )

    search.fit(X_train, y_train)
    best_model = search.best_estimator_
    #print(f"Best hyperparameters for {team}: {search.best_params_}")


    model = best_model

    y_pred = model.predict(X_test)

    '''X_test_copy = X_test.copy()
    X_test_copy["actual"] = y_test.values
    X_test_copy["predicted"] = y_pred

    misclassified_runs_as_pass = X_test_copy[(X_test_copy["actual"] == "run") & (X_test_copy["predicted"] == "pass")]
    misclassified_passes_as_run = X_test_copy[(X_test_copy["actual"] == "pass") & (X_test_copy["predicted"] == "run")]

    confused_pass_run = pd.concat([misclassified_runs_as_pass, misclassified_passes_as_run])
    #print(confused_pass_run)'''


    accuracy = accuracy_score(y_test, y_pred)

    print(f"Accuracy for {team}: {accuracy:.4f}")
    
    cm = confusion_matrix(y_test, y_pred)
    labels = sorted(y.unique())
    cm_df = pd.DataFrame(cm, index = [f"Actual: {label}" for label in labels], columns = [f"Predicted: {label}" for label in labels])
    #print(f"Confusion Matrix and Classification Report for {team}:\n{cm_df}\n")
    #print(classification_report(y_test, y_pred))

    team_models[team] = model

    model_path = os.path.join(MODEL_DIR, f"{team}_rf_model.joblib")
    joblib.dump(best_model, model_path)
    print(f"Saved model for {team} to {model_path}\n")



#print(df_team["play_type"].value_counts(normalize=True))

'''X = df[features]
X = pd.get_dummies(X, columns=["posteam_type", "defteam"], drop_first=True) # Convert categorical variables to dummy variables
y = df[target]


X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)'''

'''param_dist = {'n_estimators': randint(50,500),
              'max_depth': randint(5,30),
              'min_samples_split': randint(2, 10),
              'min_samples_leaf': randint(1, 10), 
              'max_features': ['sqrt', 'log2']}

rand_search = RandomizedSearchCV(RandomForestClassifier(random_state=42), param_distributions=param_dist, n_iter = 20, cv = 5, scoring='accuracy', n_jobs=-1, verbose=1, random_state=42)
rand_search.fit(X_train, y_train)
print("Best model:", rand_search.best_estimator_)
print("Best params:", rand_search.best_params_)

# Best params: {'max_depth': 18, 'max_features': 'sqrt', 'min_samples_leaf': 4, 'min_samples_split': 3, 'n_estimators': 409}

rf_model = RandomForestClassifier(max_depth=18, max_features='sqrt', min_samples_leaf=4, min_samples_split=3,
                       n_estimators=409, random_state=42)

rf_model.fit(X_train, y_train)
y_pred = rf_model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
#print("Accuracy:", accuracy)
cm = confusion_matrix(y_test, y_pred)
# accuracy: 0.969396

importances = rf_model.feature_importances_
feature_names = X.columns
sorted_features = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)

for feature, importance in sorted_features[:20]:
    print(f"{feature}: {importance:.4f}")'''

'''labels = sorted(y.unique())
cm_df = pd.DataFrame(cm, index = [f"Actual: {label}" for label in labels], columns = [f"Predicted: {label}" for label in labels])
print(cm_df)'''
'''
                    Predicted: field_goal  Predicted: pass  Predicted: punt  Predicted: run
Actual: field_goal                   1039                0               26              48
Actual: pass                            0            20443                0               0
Actual: punt                            8                0             2116              19
Actual: run                            14              992               41           13615
'''
#print(classification_report(y_test, y_pred))

'''
              precision    recall  f1-score   support

  field_goal       0.97      0.94      0.96      1133
        pass       0.95      1.00      0.98     20355
        punt       0.97      0.99      0.98      2151
         run       1.00      0.93      0.96     14722

    accuracy                           0.97     38361
   macro avg       0.97      0.96      0.97     38361
weighted avg       0.97      0.97      0.97     38361
'''
# Precision: accuracy of positive predictions (not to label an instance positive that is actually negative) (pass plays) (how many were actually correct) (few false positives)
# Recall: ability to find all positive casses (how many did the model correctly identify)(few false negatives)
# F1 score: what percent of positive predictions were correct
# support: number of actual positive cases in the data set''''


'''
# this is code for logistic regression model
df_combined = pd.read_csv('combined_pbp_pass_run_2024.csv', low_memory=False)

play_counts = df_combined.groupby(['posteam', 'play_type']).size().unstack(fill_value=0)
play_counts["total"] = play_counts["pass"] + play_counts["run"]
play_counts["pass_rate"] = play_counts["pass"] / play_counts["total"]
play_counts["run_rate"] = play_counts["run"] / play_counts["total"]

df_team = df_combined[df_combined["posteam"] == "PHI"].copy()

df_team["is_losing"] = (df_team["score_differential"] < 0).astype(int)
df_team["short_yardage"] = (df_team["ydstogo"] <= 3).astype(int)
df_team["medium_yardage"] = ((df_team["ydstogo"] > 3) & (df_team["ydstogo"] <= 7)).astype(int)
df_team["long_yardage"] = (df_team["ydstogo"] > 7).astype(int)
df_team["quarter_half"] = (df_team["qtr"] <= 2).astype(int)  # 1st half = 1, 2nd half = 0
df_team["clock_pressure"] = (df_team["half_seconds_remaining"] <= 120).astype(int)  # 2 minutes or less in the half
df_team["red_zone"] = (df_team["yardline_100"] <= 20).astype(int)  # within 20 yards of the end zone
df_team["late_game"] = (df_team["game_seconds_remaining"] <= 120).astype(int)

features = ["down", "ydstogo", "yardline_100", "goal_to_go", "qtr", "game_seconds_remaining", "score_differential", "posteam",
            "posteam_type", "defteam", "is_losing", "short_yardage", "late_game", "medium_yardage", "long_yardage", "quarter_half", "clock_pressure", "red_zone", "season"]
target = "play_type"

X = df_team[features]
X = pd.get_dummies(X, columns=["posteam", "posteam_type", "defteam"], drop_first=True) # Convert categorical variables to dummy variables
#print (X.columns)  # Check the columns after encoding
y = df_team[target].apply(lambda x: 1 if x == 'pass' else 0)  # 1 for pass, 0 for run
#print(y.value_counts())  # Check the distribution of the target variable

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

model = LogisticRegression(max_iter= 5000)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)

print("Accuracy:", accuracy_score(y_test, y_pred))
print(confusion_matrix(y_test, y_pred))
print(classification_report(y_test, y_pred))

# Precision: accuracy of positive predictions (not to label an instance positive that is actually negative) (pass plays)
# Recall: ability to find all positive casses
# F1 score: what percent of positive predictions were correct
# support: number of actual positive cases in the data set'''''''''
