import pandas as pd
import os
import pdb
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
from sklearn.preprocessing import StandardScaler

class CleanCombinePBP:
    #df = pd.read_csv("nfl_pbp_csvs/play_by_play_2022.csv", low_memory=False)
    #print(df.shape)
    #print(df.head())

    ## Game & Team Information ##
    # game_id = unique id for the game
    # home_combined, away_combined = abbreviations fo the teams playing in the game
    # posteam = the team that has the ball
    # posteam_type = home or away team
    # defteam = the team that is on defense
    # season_type = REG or POST (regular season or postseason)
    # week = the week of the season
    # side_of_field = the side of the file the play is on (can be either team)

    ## Time and Situation ## 
    # qtr = Quarter of the game (1-4, OT)
    # down = down number (1-4)
    # ydstogo = yards to go for a first down
    # yardline_100 = distance to opponent's end zone (0=TD)
    # game_seconds_remaining = seconds remaining in the game
    # half_seconds_remaining = seconds remaining in the current half
    # quarerter_seconds_remaining = seconds remaining in the quarter
    # game_seconds_remaining = seconds remaining in the game
    # goal_to_go = True if it's a goal-togo sittuation (10 yds or less of end zone)

    ## Play Type and Details ##
    # play_type = type of play 'pass', 'run', 'kickoff', 'punt'  --> NULL whenever the game starts, ends, quarter ends, 
    # desc = raw text description of the play
    # play_type_nfl = NFL's official classification
    # shotgun, no_huddle = boolean flags for formation type

    ## Yardage and Results ##
    #  yards_gained = yards gained on the play
    # air_yards = air distance the ball traveled
    # yards_after_catch = yards gained after the catch
    # run_location/ run_gap = direction and gap targeted during a run play
    # field_goal_result: outcome of a field goal attempt
    # kick_distance = distance of the kick
    # touchdown, pass_touchdown, rush_touchdown = booleans indicating if a touchdown was scored

    ## Advanced Metrics ##
    # epa = expected points added for the play
    # wp, home_wp, away_wp = win probability before the play
    # wpa = win probability added for the play
    # xpac_epa/ xyac_mean_yardage = expected yards after catch metrics
    # cpoe = completion percentage over expected
    # xpass = probability the play was a pass
    # pass_oe = pass over expectation (actual - exprected pass rate)

    ## Player Information ##
    # passer_player_name, receiver_player_name, rusher_player_name = names of players involved in the play
    # passing_yards, receiving_yards, rushing_yards = yards gained by the respective players
    # sack_player_name, interception_player_name = names of players involved in sacks or interceptions
    # fantasy_player_names = players credited with fantasy points
    # fantasy = fantasy points scored on the play

    ## Additional fields ##
    # penalty, penalty_type, penalty_yards = information about any penalties on the play
    # fumble, fumble_lost, fumble_recovery_player_name = information about fumbles
    # safety = indicates if the play resulted in a safety
    # two_point_attempt, two_point_conv_result = deatils about two_point conversion attempts

    #print(df["posteam"].value_counts()) # count of offensive plays by team --> eagles, chiefs, bengals, cowboys, bucs are top 5 teams
    #print(df["play_type"].value_counts()) # count of play types --> pass, run, no_play, kickoff, punt are top 5 play types (what is no_play?)
    #print(df.groupby("posteam")["epa"].mean()) # ARI, ATL, BAL, BUF, CAR are top 5 teams by average EPA per play


    # want to predict play_type
    # features:
    ## Game Situation ##
    # down = different plays on 1st vs 3rd down
    # ydstogo = teams are most likely to pass on longer distances
    # yardline_100 = field poisition (e.g. red zone)
    # goal_to_go = indicates high-pressure situations
    # qtr = late-game strategies shift (e.g. more passing in 4Q)
    # game_seconds_remaning = urgency affects play calling
    # score_differential = teams trailing are more liekely to pass the ball

    ## Team info ##
    # posteam = team tendencies differ (some pass-heavy, some run-heavy)
    # posteam_type = can encode as home or away team
    # defteam = defense might influence offensive play calling

    ## Extra Features ##
    # shotgun, no_huddle = formation and pace can indicate play type
    # side_of_field = might correlate with tendencies near the red zone

    # Will be using classication models!
    # Logistic regression can be used to predict either pass or run plays
    # Can start with this one ^^^ and then move to more complex models
    # Can use SVM
    # KNN?
    # random forest seems pretty good

    # maybe later on when predicting stuff like yards_gained, epa, etc. we can use regression models

    # data I need for web app:
    # 1. season
    # 2. game_id, game_date, home_combined, away_combined
    # 3. posteam, defteam
    #  4. play_id, desc, play_type, yards_gained -- shows plays for a team in a game
    # 5. evaluate user predicction -- actual play_type for the selected play_type
    # 6. visulization:
    # run/pass ratio -- play_type grouped by posteam
    # epa trends --  epa grouped by season, posteam
    # popular plays -- play_type frequency by posteam, situation

    def clean_data(self, valid_play_types, new_directory):
        directory = "nfl_pbp_csvs"
        # Clean play-by-play CSV files by removing rows with null play_type values
        for filename in os.listdir(directory):
            if filename.endswith(".csv"):
                path = os.path.join(directory, filename)
                df = pd.read_csv(path, low_memory=False)
                #pdb.set_trace()
                #drop rows with null play_type values and keep only valid play types
                df_cleaned = df[df["play_type"].notna()]
                df_cleaned = df_cleaned[df_cleaned["play_type"].isin(valid_play_types)]

                df_cleaned = df_cleaned[df_cleaned["two_point_attempt"] != 1]
                            
                # save to cleaned_pbp_csvs directory
                os.makedirs(new_directory, exist_ok=True)
                cleaned_path = os.path.join(new_directory, filename)
                df_cleaned.to_csv(cleaned_path, index=False)
                    
    #clean_data()

    # 2 pt conversionscdf_doown
    def combine_cleaned_data(self, directory, csv_name):
        all_dfs = []
        for filename in os.listdir(directory):
            year = int(filename.split('_')[-1].split('.')[0])
            if 2016<= year <= 2023:
                path = os.path.join(directory, filename)
                df = pd.read_csv(path, low_memory=False)
                df["season"] = year
                all_dfs.append(df)

        df_combined = pd.concat(all_dfs, ignore_index=True)
        df_combined.to_csv(csv_name, index=False)

    #combine_cleaned_data()

    def merge_participation_data(self, pbp_df, year):
        path = f"nfl_pbp_participation_csvs/pbp_participation_{year}.csv"
        if not os.path.exists(path):
            print(f"Participation data for {year} not found.")
            return pbp_df

        part_df = pd.read_csv(path, low_memory=False)

        pbp_df = pbp_df.rename(columns={"game_id": "nflverse_game_id"})
        # Merge on game_id and play_id
        merged_df = pd.merge(pbp_df, part_df, on=["nflverse_game_id", "play_id"], how="left")
        return merged_df
