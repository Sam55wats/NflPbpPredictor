//component -- piece of reusable code used in ui

//export -- makes function functional outside of file
//default tells files this is main function 
// <button> JSX element
// className tells css how to style button
import React from 'react'
import { useState, useEffect } from "react";
import { Typeahead } from 'react-bootstrap-typeahead';
import SiteChrome from './SiteChrome';
import TeamLogo from './TeamLogo';
import './gridiron-theme.css';
import './styles.css';

const getTeamById = (teams, teamId) => teams.find((team) => String(team.id) === String(teamId));
const getGameById = (games, gameId) => games.find((game) => String(game.id) === String(gameId));
const getSeasonById = (seasons, seasonId) => seasons.find((season) => String(season.id) === String(seasonId));
const MAX_SCROLLABLE_RESULTS = 1000;

export default function App() {
    const [seasons, setSeasons] = useState([]);
    const [selectedSeason, setSelectedSeason] = useState(undefined);
    const [games, setGames] = useState([]);
    const [selectedGame, setSelectedGame] = useState(undefined);
    const [teams, setTeams] = useState([]);
    const [selectedTeam, setSelectedTeam] = useState(undefined);

    
    useEffect (() => {
        console.log("fetching season api")
        fetch("/api/season/")
            .then((res) => res.json())
            .then((data) => setSeasons(data.map((season) => ({
                ...season,
                label: `${season.year} Season`
            }))));
    }, []);

    useEffect (() => {
        console.log("fetching game api")
        if (selectedSeason) { 
            fetch("/api/game/?season_id=" + selectedSeason)
                .then((res) => res.json())
                .then((data) => {
                    const formatted = data.map(game => ({
                        ...game,
                        label: `Week ${game.week}: ${game.away_team.team_name} at ${game.home_team.team_name}`
                    })); 
                    setGames(formatted);
                });
        }
    }, [selectedSeason]);

    useEffect (() => {
        console.log("fetching teams api")
        if (selectedGame) { 
            fetch("/api/teams/?game_id=" + selectedGame)
                .then((res) => res.json())
                .then((data) => setTeams(data.map((team) => ({
                    ...team,
                    label: `${team.team_abbr} - ${team.team_name}`
                }))));
        }
    }, [selectedGame]);

    const activeSeason = getSeasonById(seasons, selectedSeason);
    const activeGame = getGameById(games, selectedGame);
    const activeTeam = getTeamById(teams, selectedTeam);
    const isReady = selectedSeason && selectedGame && selectedTeam;

    return (
        <SiteChrome>
            <main className="page-wrap">
                <section className="card-panel hero-card">
                    <div className="card-body">
                        <p className="section-kicker">NFL Play Predictor</p>
                        <h1 className="page-title">Pre-snap call sheet</h1>
                        <p className="lede">
                            Pick a season, matchup, and offense to send a historical play into the model room.
                            The next screen compares the forest prediction against what actually happened.
                        </p>
                        <div className="matchup-strip">
                            <span className="meta-chip">{activeSeason ? activeSeason.label : "Season pending"}</span>
                            <span className="meta-chip">{activeGame ? `Week ${activeGame.week}` : "Game pending"}</span>
                            <span className="meta-chip">{activeTeam ? activeTeam.team_name : "Team pending"}</span>
                        </div>
                    </div>
                </section>

                <div className="dashboard-grid">
                    <section className="card-panel setup-card">
                        <div className="card-body">
                            <h2 className="section-title">Game Setup</h2>
                            <div className="control-stack">
                                <div className="field-group">
                                    <label className="field-label">Season</label>
                                    <Typeahead
                                        className="picker-typeahead"
                                        id="season-typeahead"
                                        labelKey="label"
                                        maxHeight="280px"
                                        maxResults={seasons.length || 10}
                                        options={seasons}
                                        paginate={false}
                                        placeholder="Select a season..."
                                        selected={activeSeason ? [activeSeason] : []}
                                        onChange={(selected) => {
                                            setSelectedSeason(selected.length ? selected[0].id : undefined);
                                            setSelectedGame(undefined);
                                            setSelectedTeam(undefined);
                                            setGames([]);
                                            setTeams([]);
                                        }}
                                        renderMenuItemChildren={(option) => (
                                            <div className="picker-option compact-option">
                                                <span className="picker-option-label">Season</span>
                                                <span className="picker-option-primary">{option.year} Regular Season</span>
                                            </div>
                                        )}
                                    />
                                    <span className="field-help">Available seasons are loaded from the Django API.</span>
                                </div>

                                {selectedSeason && (
                                    <div className="field-group">
                                        <label className="field-label">Game</label>
                                        <Typeahead
                                            className="picker-typeahead"
                                            id="game-typeahead"
                                            labelKey="label"
                                            maxHeight="420px"
                                            maxResults={MAX_SCROLLABLE_RESULTS}
                                            options={games}
                                            paginate={false}
                                            placeholder='Type a week number or team...'
                                            selected={activeGame ? [activeGame] : []}
                                            onChange={(selected) => {
                                                if (selected.length > 0) {
                                                    setSelectedGame(selected[0].id);
                                                    setSelectedTeam(undefined);
                                                } else {
                                                    setSelectedGame(undefined);
                                                    setSelectedTeam(undefined);
                                                }
                                            }}
                                            filterBy={(option, props) => {
                                                const inputValue = props.text.toLowerCase();

                                                return (
                                                    option.label.toLowerCase().includes(inputValue) ||
                                                    option.week.toString().includes(inputValue)
                                                );
                                            }}
                                            renderMenuItemChildren={(option) => (
                                                <div className="picker-option">
                                                    <span className="picker-option-label">Week {option.week}</span>
                                                    <span className="picker-option-primary">
                                                        <strong>{option.away_team.team_abbr}</strong> {option.away_team.team_name}
                                                        <span className="picker-option-separator"> at </span>
                                                        <strong>{option.home_team.team_abbr}</strong> {option.home_team.team_name}
                                                    </span>
                                                </div>
                                            )}
                                        />
                                        <span className="field-help">Search by week number, home team, or away team.</span>
                                    </div>
                                )}

                                {selectedGame && selectedSeason && (
                                    <div className="field-group">
                                        <label className="field-label">Offense</label>
                                        <Typeahead
                                            className="picker-typeahead"
                                            id="team-typeahead"
                                            labelKey="label"
                                            maxHeight="280px"
                                            maxResults={teams.length || 10}
                                            options={teams}
                                            paginate={false}
                                            placeholder="Select the offense..."
                                            selected={activeTeam ? [activeTeam] : []}
                                            onChange={(selected) => {
                                                setSelectedTeam(selected.length ? selected[0].id : undefined);
                                            }}
                                            renderMenuItemChildren={(option) => (
                                                <div className="team-picker-option">
                                                    <TeamLogo team={option} />
                                                    <div className="picker-option compact-option">
                                                        <span className="picker-option-label">Offense</span>
                                                        <span className="picker-option-primary">
                                                            <strong>{option.team_abbr}</strong> {option.team_name}
                                                        </span>
                                                    </div>
                                                </div>
                                            )}
                                        />
                                        <span className="field-help">Choose the possession team for the play list.</span>
                                    </div>
                                )}

                                {isReady && (
                                    <div>
                                        <a className="cta-button" href={`/analysis/?season=${selectedSeason}&game=${selectedGame}&team=${selectedTeam}`}>
                                            Go to Analysis
                                        </a>
                                    </div>
                                )}
                            </div>
                        </div>
                    </section>

                    <aside>
                        <section className="card-panel rail-card">
                            <div className="card-body">
                                <h2 className="section-title">Model Status</h2>
                                <span className="status-pill">
                                    <span className={`status-dot ${isReady ? "ready" : ""}`}></span>
                                    {isReady ? "Ready" : "Waiting"}
                                </span>
                                <ul className="headline-list mt-3">
                                    <li>Team-specific random forest models power inference.</li>
                                    <li>Saved feature lists align the selected play before prediction.</li>
                                    <li>Results reveal only after a historical play is chosen.</li>
                                </ul>
                            </div>
                        </section>
                    </aside>
                </div>
            </main>
        </SiteChrome>
        );
}
