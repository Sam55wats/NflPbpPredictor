from django.db import models

class Season(models.Model):
    year = models.IntegerField(unique=True)

    def __str__(self):
        return str(self.year)

class Team(models.Model):
    team_abbr = models.CharField(max_length=10, unique=True)
    team_name = models.CharField(max_length=100)

    def __str__(self):
        return self.team_name

class Game(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    week = models.IntegerField()
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_games')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_games')

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} (Week {self.week}, {self.season.year})"

class Play(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    posteam = models.ForeignKey(Team, on_delete=models.CASCADE)
    posteam_type = models.CharField(max_length=20, default="unknown")
    defteam = models.CharField(max_length=20, default="unknown")
    quarter = models.IntegerField()
    quarter_seconds_remaining = models.FloatField(default=0)
    down = models.IntegerField(null=True, blank=True)
    ydstogo = models.FloatField(null=True, blank=True)
    yardline_100 = models.FloatField(null=True, blank=True)
    qtr_seconds_remaining = models.IntegerField(null=True, blank=True)
    half_seconds_remaining = models.IntegerField(null=True, blank=True)
    game_seconds_remaining = models.IntegerField(null=True, blank=True)
    score_differential = models.FloatField(null=True, blank=True)
    posteam_timeouts_remaining = models.IntegerField(null=True, blank=True)
    defteam_timeouts_remaining = models.IntegerField(null=True, blank=True)
    shotgun = models.BooleanField(default=False)
    no_huddle = models.BooleanField(default=False)
    goal_to_go = models.BooleanField(default=False)
    play_type = models.CharField(max_length=20)
    time = models.CharField(max_length=20, default="unknown")

    is_losing = models.BooleanField(default=False)
    short_yardage = models.BooleanField(default=False)
    late_game = models.BooleanField(default=False)
    medium_yardage = models.BooleanField(default=False)
    long_yardage = models.BooleanField(default=False)
    quarter_half = models.IntegerField(null=True, blank=True)  # 1 for first half, 2 for second half
    clock_pressure = models.BooleanField(default=False)
    red_zone = models.BooleanField(default=False)
    season = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.posteam.team_abbr} Play in Game {self.game.id} (Q{self.quarter}, Down {self.down})"
