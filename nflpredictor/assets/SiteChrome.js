import React from 'react';

export default function SiteChrome({ children, active = "Home" }) {
    const isActive = (label) => active === label ? "league-link active" : "league-link";

    return (
        <div className="site-shell">
            <header className="scorebar">
                <a className="brand-wedge" href="/">NFL PBP</a>
                <div className="scorebar-spacer"></div>
                <a className="scorebar-link" href="/">Predictor</a>
                <a className="scorebar-link" href="/analysis/">Analysis</a>
            </header>
            <nav className="league-nav" aria-label="NFL navigation">
                <div className="league-nav-inner">
                    <a className="league-mark" href="/">
                        <span className="shield">NFL</span>
                        <span>NFL</span>
                    </a>
                    <a className={isActive("Home")} href="/">Home</a>
                    <a className={isActive("Analysis")} href="/analysis/">Analysis</a>
                </div>
            </nav>
            {children}
        </div>
    );
}
