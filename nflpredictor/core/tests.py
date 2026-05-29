from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from core.models import Game, Play, Season, Team
from core.views import build_play_features, predict_play, prepare_prediction_frame


class PredictPlayFeatureTests(TestCase):
    def setUp(self):
        self.season = Season.objects.create(year=2024)
        self.home = Team.objects.create(team_abbr="KC", team_name="Kansas City Chiefs")
        self.away = Team.objects.create(team_abbr="BUF", team_name="Buffalo Bills")
        self.game = Game.objects.create(
            season=self.season,
            week=1,
            home_team=self.home,
            away_team=self.away,
        )
        self.play = Play.objects.create(
            game=self.game,
            posteam=self.home,
            quarter=4,
            quarter_seconds_remaining=90,
            half_seconds_remaining=90,
            game_seconds_remaining=90,
            down=2,
            ydstogo=8,
            yardline_100=18,
            score_differential=-3,
            posteam_timeouts_remaining=2,
            defteam_timeouts_remaining=1,
            shotgun=True,
            no_huddle=False,
            goal_to_go=False,
            play_type="pass",
            time="01:30",
        )

    def test_build_play_features_recomputes_inference_fields(self):
        features = build_play_features(self.play)

        self.assertEqual(features["posteam_type"], "home")
        self.assertEqual(features["defteam"], "BUF")
        self.assertEqual(features["is_losing"], 1)
        self.assertEqual(features["red_zone"], 1)
        self.assertEqual(features["clock_pressure"], 1)
        self.assertEqual(features["late_game"], 1)
        self.assertEqual(features["short_yardage"], 0)
        self.assertEqual(features["medium_yardage"], 0)
        self.assertEqual(features["long_yardage"], 1)
        self.assertEqual(features["quarter_half"], 0)
        self.assertEqual(features["season"], 2024)

    def test_prepare_prediction_frame_allows_no_bucket_feature_names(self):
        features = build_play_features(self.play)
        frame = prepare_prediction_frame(
            features,
            [
                "down",
                "ydstogo",
                "yardline_100",
                "posteam_type_home",
                "defteam_BUF",
                "red_zone",
            ],
        )

        self.assertEqual(list(frame.columns), [
            "down",
            "ydstogo",
            "yardline_100",
            "posteam_type_home",
            "defteam_BUF",
            "red_zone",
        ])
        self.assertNotIn("short_yardage", frame.columns)
        self.assertEqual(frame.iloc[0]["red_zone"], 1)

    @patch("core.views.predict_with_flat_model", return_value={
        "prediction": "run",
        "model_type": "flat",
        "stage_prediction": None,
        "stage_confidence": None,
        "prediction_confidence": 0.61,
    })
    @patch("core.views.staged_models_available", return_value=False)
    def test_predict_play_falls_back_to_flat_model(self, _staged_available, _flat_predict):
        request = APIRequestFactory().get("/api/predict_play/", {"play_id": self.play.id})
        response = predict_play(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["prediction"], "run")
        self.assertEqual(response.data["actual"], "pass")
        self.assertEqual(response.data["model_type"], "flat")
        self.assertEqual(response.data["prediction_confidence"], 0.61)

    @patch("core.views.predict_with_staged_model", return_value={
        "prediction": "pass",
        "model_type": "staged",
        "stage_prediction": "offense",
        "stage_confidence": 0.88,
        "prediction_confidence": 0.72,
    })
    @patch("core.views.staged_models_available", return_value=True)
    def test_predict_play_uses_staged_model_when_available(self, _staged_available, _staged_predict):
        request = APIRequestFactory().get("/api/predict_play/", {"play_id": self.play.id})
        response = predict_play(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["prediction"], "pass")
        self.assertEqual(response.data["actual"], "pass")
        self.assertEqual(response.data["model_type"], "staged")
        self.assertEqual(response.data["stage_prediction"], "offense")
        self.assertEqual(response.data["prediction_confidence"], 0.72)
