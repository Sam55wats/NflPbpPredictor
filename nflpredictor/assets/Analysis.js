import React from 'react'
import { useState, useEffect } from "react";

import './analysis.css';
/*
1. show a list of plays (without revealing the actual outcome or model prediction)
2. user picks a play —> gets basic info (Down, distance, field position)
3. Reveal
    1. model predicted
    2. what actually happened

Data Requirements:
- Features used for model
- actual outcome: play_type
*/

export default function Analysis(){
    const [plays, setPlays] = useState([]);
    const [selectedPlay, setSelectedPlay] = useState(undefined);
    const [predictionResult, setPredictionResult] = useState(undefined);


    const [seasonYear, setSeasonYear] = useState(undefined);
    const [gameName, setGameName] = useState(undefined);
    const [teamName, setTeamName] = useState(undefined);

    const myKeysValues = window.location.search;
    console.log("keys & values: ", myKeysValues);
    const urlParams = new URLSearchParams(myKeysValues);

    const seasonId = urlParams.get("season");
    const gameId = urlParams.get("game");
    const teamId = urlParams.get("team");

    console.log("seasonId:", seasonId);
    console.log("gameId:", gameId);
    console.log("teamId:", teamId);

   useEffect(() => {
        fetch(`/api/season/`) 
            .then(res => res.json())
            .then(data => {
                const season = data.find(s => s.id === parseInt(seasonId));
                if (season) 
                    setSeasonYear(season.year);
            });

        fetch(`/api/game/?season_id=${seasonId}`)
            .then(res => res.json())
            .then(data => {
                const game = data.find(g => g.id === parseInt(gameId));
                if (game) {
                    setGameName(`${game.home_team.team_name} vs ${game.away_team.team_name} (Week ${game.week})`);
                }
            });

        fetch(`/api/teams/?game_id=${gameId}`)
            .then(res => res.json())
            .then(data => {
                const team = data.find(t => t.id === parseInt(teamId));
                if (team) 
                    setTeamName(team.team_name);
            });


        fetch(`/api/plays/?game_id=${gameId}&team_id=${teamId}`)
            .then(res => res.json())
            .then(data => setPlays(data));

    }, [seasonId, gameId, teamId]);


    return (
        <div className="container mt-5">
            <h1 className="text-center mb-4"> Game Analysis </h1>
            <h2>Season: {seasonYear}, Game: {gameName}, Team: {teamName}</h2>
            <label className='form-label'>Select a Play: </label>
            <select className='form-select' onChange={(event) => {
                const selectedId = event.target.value
                setSelectedPlay(event.target.value);

                fetch("/api/predict_play/?play_id=" + selectedId)
                    .then((res) => res.json())
                    .then((data) => {
                        setPredictionResult(data)
                    });

            }}>
                <option value="">Select a Play</option>
                { plays.map((play) => {
                    return <option key={play.id} value={play.id}>
                        Q{play.quarter} / {play.time} - {play.down}&{play.ydstogo} @ {play.yardline_100} yd line 
                    </option>

                })}

            
            </select>
            

            <br></br>
            {predictionResult && (
            <div className="prediction-box">
                <h4>Prediction: {predictionResult.prediction}</h4>
                <h4>Actual: {predictionResult.actual}</h4>
            </div>
            )}
        </div>
    )
}
