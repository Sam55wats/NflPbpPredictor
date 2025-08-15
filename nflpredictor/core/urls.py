from django.urls import path
from . import views

urlpatterns = [
    path('api/season/', views.season_list),
    path('api/game/', views.game_list),
    path('api/teams/', views.team_list),
    path('api/plays/', views.play_data),
    path('', views.home, name='home'),
    path('analysis/', views.analysis, name='analysis'),
    path("api/predict_play/", views.predict_play),

]