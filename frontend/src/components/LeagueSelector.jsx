import React from 'react';

const LeagueSelector = ({ selectedLeague, onLeagueChange }) => {
  const leagues = [
    { value: 'MLB', label: 'MLB (全リーグ)' },
    { value: 'AL', label: 'アメリカンリーグ' },
    { value: 'NL', label: 'ナショナルリーグ' }
  ];

  return (
    <div className="step-container">
      <h3>リーグを選択</h3>
      <div className="options-container">
        {leagues.map((league) => (
          <button
            key={league.value}
            className={`option-button ${selectedLeague === league.value ? 'selected' : ''}`}
            onClick={() => onLeagueChange(league.value)}
          >
            {league.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default LeagueSelector;