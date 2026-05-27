import React from 'react';

export default function SiteChrome({ children, active = "Home" }) {
    const isActive = (label) => active === label ? "league-link active" : "league-link";

    return (
        <div className="site-shell">
            <header className="scorebar">
                <a className="brand-wedge" href="/">
                    <span className="brand-football" aria-hidden="true"><span></span></span>
                    <span>PLAYCALL</span>
                </a>
                <span className="scorebar-tagline">Prediction Center</span>
                <div className="coverage-strip" aria-label="Model supported outcomes">
                    <span className="coverage-title">Model Covers</span>
                    <span>Pass</span>
                    <span>Run</span>
                    <span>Punt</span>
                    <span>Field Goal</span>
                </div>
                <a className="scorebar-action" href="/">Start Prediction</a>
            </header>
            <nav className="league-nav" aria-label="Predictor navigation">
                <div className="league-nav-inner">
                    <a className="league-mark" href="/">
                        <span className="league-football" aria-hidden="true"><span></span></span>
                        <span>Play Predictor</span>
                    </a>
                    <a className={isActive("Home")} href="/">Home</a>
                    <a className={isActive("Analysis")} href="/analysis/">Analysis</a>
                </div>
            </nav>
            {children}
        </div>
    );
}
