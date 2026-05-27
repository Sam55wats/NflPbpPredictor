import React, { useEffect, useState } from 'react';

const LOGO_CODE_BY_TEAM = {
    ARI: 'ari',
    ATL: 'atl',
    BAL: 'bal',
    BUF: 'buf',
    CAR: 'car',
    CHI: 'chi',
    CIN: 'cin',
    CLE: 'cle',
    DAL: 'dal',
    DEN: 'den',
    DET: 'det',
    GB: 'gb',
    HOU: 'hou',
    IND: 'ind',
    JAX: 'jax',
    KC: 'kc',
    LA: 'lac',
    LAC: 'lac',
    LAR: 'lar',
    LV: 'lv',
    MIA: 'mia',
    MIN: 'min',
    NE: 'ne',
    NO: 'no',
    NYG: 'nyg',
    NYJ: 'nyj',
    PHI: 'phi',
    PIT: 'pit',
    SEA: 'sea',
    SF: 'sf',
    TB: 'tb',
    TEN: 'ten',
    WAS: 'wsh',
};

export default function TeamLogo({ team, size = "menu" }) {
    const [failed, setFailed] = useState(false);
    const abbreviation = team?.team_abbr || "";
    const logoCode = LOGO_CODE_BY_TEAM[abbreviation];

    useEffect(() => {
        setFailed(false);
    }, [logoCode]);

    const className = `team-logo team-logo-${size}`;

    if (!logoCode || failed) {
        return <span className={`${className} team-logo-fallback`}>{abbreviation || "NFL"}</span>;
    }

    return (
        <span className={className}>
            <img
                alt={`${team.team_name} logo`}
                onError={() => setFailed(true)}
                src={`https://a.espncdn.com/i/teamlogos/nfl/500/${logoCode}.png`}
            />
        </span>
    );
}
