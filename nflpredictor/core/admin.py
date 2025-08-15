from django.contrib import admin
from .models import Season, Team, Game, Play
# Register your models here.

admin.site.register(Season)
admin.site.register(Team)
admin.site.register(Game)
admin.site.register(Play)
