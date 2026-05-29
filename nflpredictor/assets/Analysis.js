import React from 'react'
import { useState, useEffect } from "react";
import { Typeahead } from 'react-bootstrap-typeahead';

import SiteChrome from './SiteChrome';
import TeamLogo from './TeamLogo';
import './gridiron-theme.css';
import './styles.css';
import './analysis.css';

const MAX_SCROLLABLE_RESULTS = 1000;
const formatPercent = (value) => {
    if (value === undefined || value === null) {
        return "N/A";
    }
    return `${Math.round(value * 100)}%`;
};

const modelLabel = (modelType) => {
    if (modelType === "staged") {
        return "Staged";
    }
    if (modelType === "flat") {
        return "Flat";
    }
    return "Pending";
};

const stageLabel = (stagePrediction) => {
    if (stagePrediction === "offense") {
        return "Offense";
    }
    if (stagePrediction === "special") {
        return "Special teams";
    }
    return "Single step";
};
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
    const [game, setGame] = useState(undefined);
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
                    setGame(game);
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
            .then(data => setPlays(data.map((play) => ({
                ...play,
                label: `Q${play.quarter} ${play.time} - ${play.down}&${play.ydstogo} at ${play.yardline_100}`
            }))));

    }, [seasonId, gameId, teamId]);

    const activePlay = plays.find((play) => String(play.id) === String(selectedPlay));
    const hasResult = Boolean(predictionResult);
    const isCorrect = hasResult && predictionResult.prediction === predictionResult.actual;
    const resultClass = hasResult ? (isCorrect ? "correct" : "incorrect") : "";

    const handlePlayChange = (selected) => {
        const selectedId = selected.length ? selected[0].id : undefined;
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
                        {game ? (
                            <div className="matchup-feature" aria-label={`${game.away_team.team_name} at ${game.home_team.team_name}`}>
                                <div className="matchup-team">
                                    <TeamLogo team={game.away_team} size="hero" />
                                    <span className="matchup-abbr">{game.away_team.team_abbr}</span>
                                    <span className="matchup-name">{game.away_team.team_name}</span>
                                </div>
                                <div className="matchup-center">
                                    <span className="matchup-week">Week {game.week}</span>
                                    <span className="matchup-at">at</span>
                                </div>
                                <div className="matchup-team">
                                    <TeamLogo team={game.home_team} size="hero" />
                                    <span className="matchup-abbr">{game.home_team.team_abbr}</span>
                                    <span className="matchup-name">{game.home_team.team_name}</span>
                                </div>
                            </div>
                        ) : (
                            <h1 className="matchup-title">Loading matchup</h1>
                        )}
                        <div className="matchup-strip">
                            <span className="meta-chip">Season {seasonYear || "..."}</span>
                            <span className="meta-chip">{teamName || "Team loading"}</span>
                            <span className="meta-chip">{plays.length ? `${plays.length} eligible plays` : "Loading plays"}</span>
                        </div>
                    </div>
                </section>

                <div className="play-layout">
                    <section className="card-panel selector-card">
                        <div className="card-body">
                            <h2 className="section-title">Play Selector</h2>
                            <div className="field-group">
                                <label className='field-label'>Historical snap</label>
                                <Typeahead
                                    className="picker-typeahead snap-typeahead"
                                    id="snap-typeahead"
                                    labelKey="label"
                                    maxHeight="420px"
                                    maxResults={MAX_SCROLLABLE_RESULTS}
                                    options={plays}
                                    paginate={false}
                                    placeholder="Find a historical snap..."
                                    selected={activePlay ? [activePlay] : []}
                                    onChange={handlePlayChange}
                                    renderMenuItemChildren={(play) => (
                                        <div className="picker-option snap-option">
                                            <span className="picker-option-label">Q{play.quarter} - {play.time}</span>
                                            <span className="picker-option-primary">
                                                <strong>{play.down}&{play.ydstogo}</strong>
                                                <span className="picker-option-separator"> at </span>
                                                {play.yardline_100} yard line
                                            </span>
                                        </div>
                                    )}
                                />
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
                                        <div className="model-summary">
                                            <span className="status-pill">
                                                <span className={`status-dot ${predictionResult.model_type === "staged" ? "ready" : ""}`}></span>
                                                {modelLabel(predictionResult.model_type)} model
                                            </span>
                                            <div className="confidence-row">
                                                <div>
                                                    <span className="confidence-label">Route</span>
                                                    <strong>{stageLabel(predictionResult.stage_prediction)}</strong>
                                                </div>
                                                <span>{formatPercent(predictionResult.stage_confidence)}</span>
                                            </div>
                                            <div className="confidence-meter" aria-label="Route confidence">
                                                <span style={{ width: formatPercent(predictionResult.stage_confidence || 0) }}></span>
                                            </div>
                                        </div>
                                        <div className="result-card">
                                            <div className="result-label">Prediction</div>
                                            <div className="result-value">{predictionResult.prediction}</div>
                                            <div className="confidence-row compact">
                                                <span>Confidence</span>
                                                <strong>{formatPercent(predictionResult.prediction_confidence)}</strong>
                                            </div>
                                            <div className="confidence-meter final" aria-label="Prediction confidence">
                                                <span style={{ width: formatPercent(predictionResult.prediction_confidence || 0) }}></span>
                                            </div>
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
