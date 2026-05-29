from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Backfill engineered and categorical play features used by inference."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE core_play
                SET
                    is_losing = CASE WHEN score_differential < 0 THEN 1 ELSE 0 END,
                    short_yardage = CASE WHEN ydstogo <= 3 THEN 1 ELSE 0 END,
                    medium_yardage = CASE WHEN ydstogo > 3 AND ydstogo <= 7 THEN 1 ELSE 0 END,
                    long_yardage = CASE WHEN ydstogo > 7 THEN 1 ELSE 0 END,
                    late_game = CASE WHEN game_seconds_remaining <= 120 THEN 1 ELSE 0 END,
                    quarter_half = CASE WHEN quarter <= 2 THEN 1 ELSE 0 END,
                    clock_pressure = CASE WHEN half_seconds_remaining <= 120 THEN 1 ELSE 0 END,
                    red_zone = CASE WHEN yardline_100 <= 20 THEN 1 ELSE 0 END,
                    season = (
                        SELECT core_season.year
                        FROM core_game
                        JOIN core_season ON core_season.id = core_game.season_id
                        WHERE core_game.id = core_play.game_id
                    ),
                    posteam_type = (
                        SELECT CASE
                            WHEN core_play.posteam_id = core_game.home_team_id THEN 'home'
                            ELSE 'away'
                        END
                        FROM core_game
                        WHERE core_game.id = core_play.game_id
                    ),
                    defteam = (
                        SELECT CASE
                            WHEN core_play.posteam_id = core_game.home_team_id THEN away_team.team_abbr
                            ELSE home_team.team_abbr
                        END
                        FROM core_game
                        JOIN core_team AS home_team ON home_team.id = core_game.home_team_id
                        JOIN core_team AS away_team ON away_team.id = core_game.away_team_id
                        WHERE core_game.id = core_play.game_id
                    )
                """
            )

        self.stdout.write(self.style.SUCCESS("Backfilled play inference features."))
