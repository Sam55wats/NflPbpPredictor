from django.core.management.base import BaseCommand
from core.models import Season, Team, Game, Play
import pandas as pd
import os

MODE_REFRESH = 'refresh'
MODE_CLEAR = 'clear'

TEAM_NAME_MAP = {"ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens", "BUF": "Buffalo Bills",
                 "CAR": "Carolina Panthers", "CHI": "Chicago Bears", "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns",
                 "DAL": "Dallas Cowboys", "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
                 "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs",
                 "LV": "Las Vegas Raiders", "LA": "Los Angeles Chargers", "LAC": "Los Angeles Chargers", "LAR": "Los Angeles Rams", "MIA": "Miami Dolphins",
                 "MIN": "Minnesota Vikings", "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
                 "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers", "SF": "San Francisco 49ers",
                 "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans", "WAS": "Washington Commanders"
                 }

class Command(BaseCommand):
    help = 'seed database from CSV'

    def add_arguments(self, parser):
        parser.add_argument('--mode', type=str, help="Mode")
    
    def handle(self, *args, **options):
        self.stdout.write("started...")
        run_seed(options['mode'])
        self.stdout.write("Done.")

def clear_data():
    Play.objects.all().delete()
    Game.objects.all().delete()
    Team.objects.all().delete()
    Season.objects.all().delete()

def run_seed(mode):
    if mode == 'clear':
        clear_data()
        return
    elif mode == 'refresh':
        clear_data()
    
    csv_path = '/Users/samuelkim/NflPbpPredictor/combined_pbp_2024_forest.csv'

    df = pd.read_csv(csv_path, low_memory=False)

    for _, row in df.iterrows():
        season_obj, _ = Season.objects.get_or_create(year=row['season'])

        home_team, _ = Team.objects.get_or_create(
        team_abbr=row['home_team'],
        defaults={"team_name": TEAM_NAME_MAP.get(row['home_team'], row['home_team'])}
        )
        away_team, _ = Team.objects.get_or_create(
        team_abbr=row['away_team'],
        defaults={"team_name": TEAM_NAME_MAP.get(row['away_team'], row['away_team'])}
        )
        posteam_obj, _ = Team.objects.get_or_create(
        team_abbr=row['posteam'],
        defaults={"team_name": TEAM_NAME_MAP.get(row['posteam'], row['posteam'])}
        )

        game_obj, _ = Game.objects.get_or_create(
            season=season_obj,
            week=row['week'],
            home_team=home_team,
            away_team=away_team
        )

        Play.objects.create(
            game=game_obj,
            posteam=posteam_obj,
            down=row['down'],
            ydstogo=row['ydstogo'],
            quarter=row['qtr'],
            quarter_seconds_remaining=row['quarter_seconds_remaining'],
            half_seconds_remaining=row['half_seconds_remaining'],
            game_seconds_remaining=row['game_seconds_remaining'],
            score_differential=row['score_differential'],
            posteam_timeouts_remaining=row['posteam_timeouts_remaining'],
            defteam_timeouts_remaining=row['defteam_timeouts_remaining'],
            shotgun=row['shotgun'],
            no_huddle=row['no_huddle'],
            goal_to_go=row['goal_to_go'],
            yardline_100=row['yardline_100'],
            play_type=row['play_type'],
            time=row['time']
        )