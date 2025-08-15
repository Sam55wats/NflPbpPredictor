from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import SeasonSerializer, GameSerializer, TeamSerializer, PlaySerializer
from .models import Season, Game, Team, Play
from django.shortcuts import render 
from django.template import loader
from django.http import HttpResponse
import os
import joblib
import pandas as pd
from django.conf import settings


@api_view(['GET'])
def season_list(request):
    seasons = Season.objects.all().order_by('-year')
    serializer = SeasonSerializer(seasons, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def game_list(request):
    season_id = request.GET.get('season_id')
    games = Game.objects.filter(season_id=season_id).select_related('home_team', 'away_team')
    serializer = GameSerializer(games, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def team_list(request):
    game_id = request.GET.get('game_id')
    game = Game.objects.select_related('home_team', 'away_team').get(id=game_id)
    team = [game.home_team, game.away_team]
    serializer = TeamSerializer(team, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def play_data(request):
    game_id = request.GET.get('game_id')
    team_id = request.GET.get('team_id')

    plays = Play.objects.filter(game_id=game_id, posteam_id=team_id)
    serializer = PlaySerializer(plays, many=True)
    return Response(serializer.data)

TEAM_ABBR = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS"
}

@api_view(['GET'])
def predict_play(request):
    play_id = request.GET.get('play_id')
    print("Received play_id:", play_id)


    play = Play.objects.get(id=play_id)

    model_path = os.path.join("saved_team_models", f"{play.posteam.team_abbr}_rf_model.joblib")

    model = joblib.load(model_path)

    play_data = {
        'down': play.down,
        'ydstogo': play.ydstogo,
        'yardline_100': play.yardline_100,
        'qtr': play.quarter,
        'quarter_seconds_remaining': play.quarter_seconds_remaining,
        'half_seconds_remaining': play.half_seconds_remaining,
        'game_seconds_remaining': play.game_seconds_remaining,
        'score_differential': play.score_differential,
        'posteam_timeouts_remaining': play.posteam_timeouts_remaining,
        'defteam_timeouts_remaining': play.defteam_timeouts_remaining,
        'shotgun': int(play.shotgun),
        'no_huddle': int(play.no_huddle),
        'goal_to_go': int(play.goal_to_go),
        'posteam_type': play.posteam_type,
        'defteam': play.defteam,
        'is_losing': int(play.is_losing),
        'short_yardage': int(play.short_yardage),
        'late_game': int(play.late_game),
        'medium_yardage': int(play.medium_yardage),
        'long_yardage': int(play.long_yardage),
        'quarter_half': play.quarter_half,
        'clock_pressure': int(play.clock_pressure),
        'red_zone': int(play.red_zone),
        'season': play.season,
    }

    df = pd.DataFrame([play_data])
    df = pd.get_dummies(df, columns=["posteam_type", "defteam"], drop_first=True)

    feature_names_path = os.path.join("saved_team_models", f"{play.posteam.team_abbr}_feature_names.joblib")
    feature_names = joblib.load(feature_names_path)
    
    df = df.reindex(columns=feature_names, fill_value=0)

    prediction = model.predict(df)[0]

    return Response({
        "prediction": prediction,
        "actual": play.play_type
    })

def home(request):
    template = loader.get_template('home.html')
    return HttpResponse(template.render())

def analysis(request):
    template = loader.get_template('analysis.html')
    return HttpResponse(template.render())