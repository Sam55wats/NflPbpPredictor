//component -- piece of reusable code used in ui

//export -- makes function functional outside of file
//default tells files this is main function 
// <button> JSX element
// className tells css how to style button
import React from 'react'
import { useState, useEffect } from "react";
import { Typeahead } from 'react-bootstrap-typeahead';
import './styles.css';



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
            .then((data) => setSeasons(data));
    }, []);

    useEffect (() => {
        console.log("fetching game api")
        if (selectedSeason) { 
            fetch("/api/game/?season_id=" + selectedSeason)
                .then((res) => res.json())
                .then((data) => {
                    const formatted = data.map(game => ({
                        ...game,
                        label: `Week ${game.week}: ${game.home_team.team_name} vs ${game.away_team.team_name}`
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
                .then((data) => setTeams(data));
        }
    }, [selectedGame]);

    return (
        <div className="container mt-5">
            <h1 className="text-center mb-4"> Welcome to the NFL Play Predictor! </h1>


            <div className="mb-3">
                <div className = "col-md-6">
                    <label className="form-label">Step 1: Select a Season:</label>
                    <select className="form-select" onChange={(event) => {
                        setSelectedSeason(event.target.value);
                        setSelectedGame(undefined);
                        setSelectedTeam(undefined);

                         }}>
                        <option value="">Select a Season</option>
                        { seasons.map((season) => {
                            return <option key = {season.id} value = {season.id}> {season["year"]}</option>
                        })}
                    
                    </select>
                </div>
            </div>
            

            {selectedSeason && (
                <div className="mb-3">
                    <label className="form-label">Step 2: Select a Game:</label>
                    <Typeahead
                        id="game-typeahead"
                        labelKey="label"
                        options={games}
                        placeholder='Type a week number...'
                        onChange={(selected) => {
                            if (selected.length > 0) {
                                setSelectedGame(selected[0].id);
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
                    />
                </div>
                )}
               


            {selectedGame && selectedSeason && (
            <div className="mb-3">
                <label className="form-label">Step 3: Select a Team:</label>
                <select className="form-select" onChange={(event) => {
                    setSelectedTeam(event.target.value);
                }}>
                <option value="">Select a Team</option>
                {teams.map((team) => (
                    <option key={team.id} value={team.id}>{team.team_abbr}</option>
                ))}
                </select>
            </div>
            )}

            {selectedSeason && selectedGame && selectedTeam && (
            <div className="text-center mt-4">
                <a className="btn btn-primary" href={`/analysis/?season=${selectedSeason}&game=${selectedGame}&team=${selectedTeam}`}>
                Go to Analysis
                </a>
            </div>
            )}
        </div>
        );
}
