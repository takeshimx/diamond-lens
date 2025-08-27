import { useState, useRef, useEffect, useCallback } from 'react';
import { Search, User, X } from 'lucide-react';

const PlayerAutocomplete = ({ selectedPlayer, onPlayerSelect, isActive, onSearchPlayers}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [filteredPlayers, setFilteredPlayers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const searchInputRef = useRef(null);

  const fetchPlayers = useCallback(async (query) => {
    if (!query) {
      setFilteredPlayers([]);
      return;
    }
    setIsLoading(true);
    
    try {
      // call function onSearchPlayers
      const players = await onSearchPlayers(query);
      
      // If API returns results, use them
      if (players && players.length > 0) {
        setFilteredPlayers(players.slice(0, 10)); // Limit to 10 results
      } else {
        // Fallback to mock data if API returns no results
        const fallbackResults = mockPlayers.filter(player => 
          player.name.toLowerCase().includes(query.toLowerCase()) ||
          player.name_en.toLowerCase().includes(query.toLowerCase()) ||
          player.team.toLowerCase().includes(query.toLowerCase())
        ).slice(0, 10);
        setFilteredPlayers(fallbackResults);
      }
    } catch (error) {
      console.error('Player search error:', error);
      // Fallback to mock data on error
      const fallbackResults = mockPlayers.filter(player => 
        player.name.toLowerCase().includes(query.toLowerCase()) ||
        player.name_en.toLowerCase().includes(query.toLowerCase()) ||
        player.team.toLowerCase().includes(query.toLowerCase())
      ).slice(0, 10);
      setFilteredPlayers(fallbackResults);
    }
    
    setIsLoading(false);
  }, [onSearchPlayers]);
  
  // Mock player data - in real implementation, this would come from API
  const mockPlayers = [
    { id: 660271, name: '大谷翔平', name_en: 'Shohei Ohtani', team: 'LAA', league: 'AL' },
    { id: 545361, name: 'マイク・トラウト', name_en: 'Mike Trout', team: 'LAA', league: 'AL' },
    { id: 592450, name: 'ムーキー・ベッツ', name_en: 'Mookie Betts', team: 'LAD', league: 'NL' },
    { id: 596019, name: 'アーロン・ジャッジ', name_en: 'Aaron Judge', team: 'NYY', league: 'AL' },
    { id: 408234, name: 'クレイトン・カーショウ', name_en: 'Clayton Kershaw', team: 'LAD', league: 'NL' },
    { id: 502110, name: 'ホセ・アルトゥーベ', name_en: 'Jose Altuve', team: 'HOU', league: 'AL' },
    { id: 608369, name: '前田健太', name_en: 'Kenta Maeda', team: 'MIN', league: 'AL' },
    { id: 553882, name: 'ダルビッシュ有', name_en: 'Yu Darvish', team: 'SD', league: 'NL' },
    { id: 666201, name: '鈴木誠也', name_en: 'Seiya Suzuki', team: 'CHC', league: 'NL' },
    { id: 678394, name: 'フアン・ソト', name_en: 'Juan Soto', team: 'SD', league: 'NL' }
  ];

  // Search players using API when search term changes
  useEffect(() => {
    if (!searchTerm) {
      setFilteredPlayers([]);
      return;
    }

    // Add debouncing to avoid too many API calls
    const timeoutId = setTimeout(() => {
      fetchPlayers(searchTerm);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchTerm, fetchPlayers]);

  const handleInputChange = (e) => {
    const value = e.target.value;
    setSearchTerm(value);
    setIsOpen(value.length > 0);
  };

  const handlePlayerSelect = (player) => {
    // Normalize player object to have consistent format
    const normalizedPlayer = {
      id: player.idfg || player.mlb_id || player.id,
      idfg: player.idfg,
      mlb_id: player.mlb_id, 
      name: player.player_name || player.name,
      name_en: player.name_en,
      player_name: player.player_name || player.name,
      team: player.team,
      league: player.league
    };
    
    onPlayerSelect(normalizedPlayer);
    setSearchTerm(player.player_name || player.name);
    setIsOpen(false);
  };

  const handleClearSelection = () => {
    onPlayerSelect(null);
    setSearchTerm('');
    setIsOpen(false);
    if (searchInputRef.current) {
      searchInputRef.current.focus();
    }
  };

  const handleInputFocus = () => {
    if (searchTerm && filteredPlayers.length > 0) {
      setIsOpen(true);
    }
  };

  const handleInputBlur = () => {
    // Delay closing to allow click events on dropdown items
    setTimeout(() => setIsOpen(false), 200);
  };

  // Set initial search term when player is selected externally
  useEffect(() => {
    const playerName = selectedPlayer?.player_name || selectedPlayer?.name;
    if (selectedPlayer && searchTerm !== playerName) {
      setSearchTerm(playerName);
    }
  }, [selectedPlayer, searchTerm]);

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className={`text-xl font-semibold mb-2 transition-colors duration-200 ${
          isActive ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-400'
        }`}>
          選手を選択
        </h3>
        <p className={`text-sm transition-colors duration-200 ${
          isActive ? 'text-gray-600 dark:text-gray-300' : 'text-gray-500 dark:text-gray-500'
        }`}>
          分析対象の選手名を検索して選択してください
        </p>
      </div>

      <div className="max-w-lg mx-auto relative">
        {/* Search Input */}
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className={`h-5 w-5 transition-colors duration-200 ${
              isActive ? 'text-gray-400 dark:text-gray-500' : 'text-gray-300 dark:text-gray-600'
            }`} />
          </div>
          
          <input
            ref={searchInputRef}
            type="text"
            value={searchTerm}
            onChange={handleInputChange}
            onFocus={handleInputFocus}
            onBlur={handleInputBlur}
            disabled={!isActive}
            placeholder="選手名またはチーム名で検索..."
            className={`
              w-full pl-10 pr-10 py-3 border rounded-lg transition-all duration-200 text-base
              ${isActive 
                ? 'border-gray-300 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 focus:border-transparent' 
                : 'border-gray-200 dark:border-gray-700 opacity-60 cursor-not-allowed'
              }
              bg-white dark:bg-gray-800 text-gray-900 dark:text-white
              placeholder-gray-500 dark:placeholder-gray-400
            `}
          />

          {selectedPlayer && (
            <button
              onClick={handleClearSelection}
              disabled={!isActive}
              className={`
                absolute inset-y-0 right-0 pr-3 flex items-center transition-colors duration-200
                ${isActive ? 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300' : 'text-gray-300'}
              `}
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>

        {/* Loading Indicator */}
        {isOpen && isLoading && (
          <div className="absolute z-50 w-full mt-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
            <div className="px-4 py-6 text-center text-gray-500 dark:text-gray-400">
              <div className="flex items-center justify-center space-x-2">
                <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                <span className="text-sm">選手を検索中...</span>
              </div>
            </div>
          </div>
        )}

        {/* Dropdown Results */}
        {isOpen && !isLoading && filteredPlayers.length > 0 && (
          <div className="absolute z-50 w-full mt-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-80 overflow-y-auto">
            {filteredPlayers.map((player, index) => (
              <button
                key={player.idfg || player.mlb_id || index}
                onClick={() => handlePlayerSelect(player)}
                className={`
                  w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700 
                  transition-colors duration-150 flex items-center space-x-3
                  ${index === 0 ? 'rounded-t-lg' : ''}
                  ${index === filteredPlayers.length - 1 ? 'rounded-b-lg' : 'border-b border-gray-200 dark:border-gray-700'}
                `}
              >
                <div className="flex-shrink-0">
                  <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  </div>
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-gray-900 dark:text-white">
                      {player.player_name || player.name}
                    </span>
                    {player.name_en && (
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        ({player.name_en})
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-2 mt-1">
                    {(player.team || player.league) && (
                      <>
                        {player.team && (
                          <span className="inline-flex px-2 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded">
                            {player.team}
                          </span>
                        )}
                        {player.league && (
                          <span className="text-sm text-gray-600 dark:text-gray-300">
                            {player.league}
                          </span>
                        )}
                      </>
                    )}
                    {/* Show IDs for API response players */}
                    {(player.idfg || player.mlb_id) && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        ID: {player.idfg || player.mlb_id}
                      </span>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* No Results */}
        {isOpen && !isLoading && searchTerm && filteredPlayers.length === 0 && (
          <div className="absolute z-50 w-full mt-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
            <div className="px-4 py-6 text-center text-gray-500 dark:text-gray-400">
              <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">「{searchTerm}」に一致する選手が見つかりません</p>
            </div>
          </div>
        )}
      </div>

      {/* Selected Player Display */}
      {selectedPlayer && (
        <div className="max-w-lg mx-auto mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
              <User className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <span className="font-medium text-blue-900 dark:text-blue-100">
                  選択中の選手
                </span>
              </div>
              <div className="mt-1">
                <span className="text-lg font-semibold text-blue-900 dark:text-blue-100">
                  {selectedPlayer.player_name || selectedPlayer.name}
                </span>
                {selectedPlayer.name_en && (
                  <span className="text-blue-700 dark:text-blue-200 ml-2">
                    ({selectedPlayer.name_en})
                  </span>
                )}
              </div>
              <div className="flex items-center space-x-2 mt-1">
                {selectedPlayer.team && (
                  <span className="inline-flex px-2 py-0.5 text-xs font-medium bg-blue-200 dark:bg-blue-800 text-blue-800 dark:text-blue-200 rounded">
                    {selectedPlayer.team}
                  </span>
                )}
                {selectedPlayer.league && (
                  <span className="text-sm text-blue-700 dark:text-blue-200">
                    {selectedPlayer.league}
                  </span>
                )}
                {(selectedPlayer.idfg || selectedPlayer.mlb_id) && (
                  <span className="text-xs text-blue-600 dark:text-blue-300">
                    ID: {selectedPlayer.idfg || selectedPlayer.mlb_id}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Popular Players Shortcut */}
      {!selectedPlayer && !searchTerm && (
        <div className="max-w-lg mx-auto">
          <h4 className={`text-sm font-medium mb-3 transition-colors duration-200 ${
            isActive ? 'text-gray-700 dark:text-gray-300' : 'text-gray-500 dark:text-gray-500'
          }`}>
            人気選手
          </h4>
          <div className="flex flex-wrap gap-2">
            {mockPlayers.slice(0, 6).map((player) => (
              <button
                key={player.id}
                onClick={() => handlePlayerSelect(player)}
                disabled={!isActive}
                className={`
                  px-3 py-1.5 text-sm rounded-full border transition-all duration-200
                  ${isActive 
                    ? 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-blue-500 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20' 
                    : 'border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-600 cursor-not-allowed'
                  }
                  bg-white dark:bg-gray-800
                `}
              >
                {player.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PlayerAutocomplete;