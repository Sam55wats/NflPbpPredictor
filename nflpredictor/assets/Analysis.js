import React from 'react'
import { useState, useEffect } from "react";

import SiteChrome from './SiteChrome';
import './espn-theme.css';
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

    const activePlay = plays.find((play) => String(play.id) === String(selectedPlay));
    const hasResult = Boolean(predictionResult);
    const isCorrect = hasResult && predictionResult.prediction === predictionResult.actual;
    const resultClass = hasResult ? (isCorrect ? "correct" : "incorrect") : "";

    const handlePlayChange = (event) => {
        const selectedId = event.target.value;
        setSelectedPlay(selectedId);
        setPredictionResult(undefined);

        if (!selectedId) {
            return;
        }

        fetch("/api/predict_play/?play_id=" + selectedId)
            .then((res) => res.json())
            .then((data) => {
                setPredictionResult(data)
            });
    };

    return (
        <SiteChrome active="Analysis">
            <main className="page-wrap">
                <section className="card-panel hero-card">
                    <div className="card-body analysis-header">
                        <p className="section-kicker">Game Analysis</p>
                        <h1 className="matchup-title">
                            {gameName || "Loading matchup"}
                        </h1>
                        <div className="matchup-strip">
                            <span className="meta-chip">Season {seasonYear || "..."}</span>
                            <span className="meta-chip">{teamName || "Team loading"}</span>
                            <span className="meta-chip">{plays.length ? `${plays.length} eligible plays` : "Loading plays"}</span>
                        </div>
                    </div>
                </section>

                <div className="play-layout">
                    <section className="card-panel">
                        <div className="card-body">
                            <h2 className="section-title">Play Selector</h2>
                            <div className="field-group">
                                <label className='field-label'>Historical snap</label>
                                <select className='form-select' value={selectedPlay || ""} onChange={handlePlayChange}>
                                    <option value="">Select a Play</option>
                                    { plays.map((play) => {
                                        return <option key={play.id} value={play.id}>
                                            Q{play.quarter} / {play.time} - {play.down}&{play.ydstogo} @ {play.yardline_100} yd line
                                        </option>
                                    })}
                                </select>
                                <span className="field-help">Choose a pre-snap situation to reveal the model pick.</span>
                            </div>

                            {activePlay && (
                                <div className="play-detail">
                                    <div className="stat-box">
                                        <div className="stat-label">Quarter</div>
                                        <div className="stat-value">Q{activePlay.quarter}</div>
                                    </div>
                                    <div className="stat-box">
                                        <div className="stat-label">Clock</div>
                                        <div className="stat-value">{activePlay.time}</div>
                                    </div>
                                    <div className="stat-box">
                                        <div className="stat-label">Down/Distance</div>
                                        <div className="stat-value">{activePlay.down}&{activePlay.ydstogo}</div>
                                    </div>
                                    <div className="stat-box">
                                        <div className="stat-label">Yard Line</div>
                                        <div className="stat-value">{activePlay.yardline_100}</div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </section>

                    <aside>
                        <section className={`card-panel prediction-outcome ${resultClass}`}>
                            <div className="card-body">
                                <h2 className="section-title">Model Pick</h2>
                                {hasResult ? (
                                    <div className="prediction-grid">
                                        <div className="result-card">
                                            <div className="result-label">Prediction</div>
                                            <div className="result-value">{predictionResult.prediction}</div>
                                        </div>
                                        <div className="result-card">
                                            <div className="result-label">Actual Result</div>
                                            <div className="result-value">{predictionResult.actual}</div>
                                        </div>
                                        <span className="status-pill">
                                            <span className={`status-dot ${isCorrect ? "ready" : ""}`}></span>
                                            {isCorrect ? "Model matched" : "Model missed"}
                                        </span>
                                    </div>
                                ) : (
                                    <div className="prediction-grid">
                                        <span className="status-pill">
                                            <span className="status-dot"></span>
                                            Awaiting play
                                        </span>
                                        <ul className="headline-list">
                                            <li>Pick a snap to call the team-specific model.</li>
                                            <li>Prediction and actual result reveal side by side.</li>
                                            <li>Pass, run, punt, and field goal are supported outcomes.</li>
                                        </ul>
                                    </div>
                                )}
                            </div>
                        </section>

                        <section className="card-panel rail-card">
                            <div className="card-body">
                                <h2 className="section-title">Game Context</h2>
                                <div className="info-row">
                                    <span className="info-label">Season</span>
                                    <span className="info-value">{seasonYear || "..."}</span>
                                </div>
                                <div className="info-row">
                                    <span className="info-label">Team</span>
                                    <span className="info-value">{teamName || "..."}</span>
                                </div>
                                <div className="info-row">
                                    <span className="info-label">Plays</span>
                                    <span className="info-value">{plays.length || "..."}</span>
                                </div>
                            </div>
                        </section>
                    </aside>
                </div>
            </main>
        </SiteChrome>
    )
}
