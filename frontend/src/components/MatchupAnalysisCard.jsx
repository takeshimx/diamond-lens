import React from 'react';

/**
 * StrikeZoneMap
 * 3x3 のストライクゾーンを簡易的に視覚化。
 */
const StrikeZoneMap = ({ zoneSequence }) => {
    if (!zoneSequence) return null;
    const zones = zoneSequence.split(',').map(z => parseInt(z.trim()));

    const grid = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9]
    ];

    return (
        <div className="flex flex-col items-center gap-1">
            <div className="grid grid-cols-3 gap-0.5 w-12 h-14 border border-gray-400 dark:border-gray-600 p-0.5 bg-gray-100/50 dark:bg-gray-900/50">
                {grid.flat().map((z) => {
                    const isHit = zones.includes(z);
                    const count = zones.filter(pz => pz === z).length;
                    return (
                        <div
                            key={z}
                            className={`relative flex items-center justify-center text-[6px] font-bold rounded-sm border ${isHit
                                ? 'bg-blue-500/40 border-blue-400 text-blue-100'
                                : 'bg-transparent border-gray-300 dark:border-gray-700 text-transparent'
                                }`}
                        >
                            {count > 1 ? count : ''}
                        </div>
                    );
                })}
            </div>
            <div className="flex gap-0.5 mt-0.5">
                {zones.filter(z => z > 9).length > 0 && (
                    <div className="text-[8px] text-gray-400 font-mono">
                        Outs: {zones.filter(z => z > 9).length}
                    </div>
                )}
            </div>
        </div>
    );
};

/**
 * MatchupAnalysisCard (Quality Enhancement & KPI Expansion)
 */
const MatchupAnalysisCard = ({ matchupData }) => {
    if (!matchupData || !matchupData.summary) return null;

    const { stats, history, summary } = matchupData;

    // 全体統計の計算 (簡易版)
    const totalStats = stats && stats.length > 0 ? {
        avg: stats.reduce((acc, s) => acc + (s.batting_average * s.pitch_count), 0) / stats.reduce((acc, s) => acc + s.pitch_count, 0),
        pa: stats.reduce((acc, s) => acc + (s.at_bats || 0), 0),
        hr: stats.reduce((acc, s) => acc + (s.homeruns || 0), 0),
        so: stats.reduce((acc, s) => acc + (s.strikeouts || 0), 0),
        bb: stats.reduce((acc, s) => acc + (s.walks || 0), 0),
        obp: stats.reduce((acc, s) => acc + (s.on_base_percentage * s.pitch_count), 0) / stats.reduce((acc, s) => acc + s.pitch_count, 0),
        ops: stats.reduce((acc, s) => acc + (s.ops * s.pitch_count), 0) / stats.reduce((acc, s) => acc + s.pitch_count, 0),
        whiff: stats.reduce((acc, s) => acc + (s.whiff_rate * s.pitch_count), 0) / stats.reduce((acc, s) => acc + s.pitch_count, 0),
        hardHit: stats.reduce((acc, s) => acc + (s.hard_hit_rate * s.pitch_count), 0) / stats.reduce((acc, s) => acc + s.pitch_count, 0),
    } : null;

    const getResultStyles = (result) => {
        const r = result?.toLowerCase() || '';
        if (r.includes('home run')) return 'bg-red-500/20 text-red-500 border-red-500/30';
        if (r.includes('single') || r.includes('double') || r.includes('triple') || r.includes('hit'))
            return 'bg-green-500/20 text-green-500 border-green-500/30';
        if (r.includes('walk')) return 'bg-blue-500/20 text-blue-500 border-blue-500/30';
        if (r.includes('out') || r.includes('strikeout') || r.includes('pop') || r.includes('fly') || r.includes('ground'))
            return 'bg-gray-500/10 text-gray-400 border-gray-500/20 opacity-80';
        return 'bg-gray-100 dark:bg-gray-800 text-gray-500 border-gray-200 dark:border-gray-700';
    };

    const getBadgeColor = (result) => {
        const r = result?.toLowerCase() || '';
        if (r.includes('home run')) return 'bg-red-500 text-white';
        if (r.includes('hit') || r.includes('single') || r.includes('double') || r.includes('triple')) return 'bg-green-500 text-white';
        if (r.includes('walk')) return 'bg-blue-500 text-white';
        if (r.includes('out') || r.includes('strikeout')) return 'bg-red-500/60 text-white';
        return 'bg-gray-400 text-white';
    };

    return (
        <div className="mt-4 p-5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm overflow-hidden transition-all duration-300 hover:shadow-md w-full max-w-2xl">
            {/* ヘッダー */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-xl">
                        <span className="text-xl font-bold">⚾</span>
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-gray-800 dark:text-white leading-tight">
                            {summary.batter} vs {summary.pitcher}
                        </h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400 font-bold tracking-wide">MATCHUP STATS 2025</p>
                    </div>
                </div>
            </div>

            {/* 主要統計グリッド (KPI 8項目) */}
            {totalStats && (
                <div className="grid grid-cols-4 gap-2 mb-6">
                    {[
                        { label: 'AVG', value: isNaN(totalStats.avg) ? '.000' : totalStats.avg.toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 }), color: 'text-gray-800 dark:text-white' },
                        { label: 'OBP', value: isNaN(totalStats.obp) ? '.000' : totalStats.obp.toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 }), color: 'text-gray-800 dark:text-white' },
                        { label: 'OPS', value: isNaN(totalStats.ops) ? '.000' : totalStats.ops.toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 }), color: 'text-blue-500' },
                        { label: 'PA', value: totalStats.pa || 0, color: 'text-gray-800 dark:text-white' },
                        { label: 'HR', value: totalStats.hr || 0, color: 'text-red-500' },
                        { label: 'K/BB', value: `${totalStats.so}/${totalStats.bb}`, color: 'text-gray-800 dark:text-white' },
                        { label: 'Whiff%', value: isNaN(totalStats.whiff) ? '0%' : `${Math.round(totalStats.whiff * 100)}%`, color: 'text-purple-500' },
                        { label: 'HardHit%', value: isNaN(totalStats.hardHit) ? '0%' : `${Math.round(totalStats.hardHit * 100)}%`, color: 'text-orange-500' },
                    ].map((stat, i) => (
                        <div key={i} className="p-2.5 bg-gray-50 dark:bg-gray-900/30 rounded-xl border border-gray-100 dark:border-gray-700/50 text-center flex flex-col justify-center min-h-[64px]">
                            <p className="text-[10px] text-gray-500 uppercase font-black tracking-tighter mb-1">{stat.label}</p>
                            <p className={`text-lg font-black leading-none ${stat.color}`}>{stat.value}</p>
                        </div>
                    ))}
                </div>
            )}

            {/* 履歴リスト (直近5件) */}
            {history && history.length > 0 && (
                <div className="mb-6">
                    <div className="flex items-center justify-between px-1 mb-3">
                        <h4 className="text-xs font-black text-gray-400 uppercase tracking-widest">Recent At-Bats</h4>
                        <span className="text-[10px] text-gray-400 font-bold bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">LIVE STATCAST</span>
                    </div>
                    <div className="space-y-3">
                        {history.slice(0, 5).map((h, i) => (
                            <div key={i} className={`flex items-start justify-between p-3 rounded-2xl border transition-all hover:scale-[1.01] ${getResultStyles(h.result)}`}>
                                <div className="flex gap-4">
                                    <div className={`w-12 h-12 flex items-center justify-center text-xs font-black rounded-xl shadow-inner ${getBadgeColor(h.result)}`}>
                                        {h.result?.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() || 'OUT'}
                                    </div>

                                    <div className="flex flex-col justify-center">
                                        <p className="text-sm font-black mb-0.5 leading-none capitalize">
                                            {h.result?.replace(/_/g, ' ') || 'Process...'}
                                        </p>
                                        <p className="text-[10px] font-bold opacity-70 mb-1">
                                            {h.game_date} • {h.pitch_name || 'In-play'}
                                        </p>
                                        <p className="text-[11px] font-medium leading-tight max-w-[280px]">
                                            {h.description || 'Description pending...'}
                                        </p>
                                    </div>
                                </div>

                                {h.zone_sequence && (
                                    <div className="hidden sm:block ml-2 border-l border-current/10 pl-4">
                                        <StrikeZoneMap zoneSequence={h.zone_sequence} />
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* 球種別内訳 (Visual) */}
            {stats && stats.length > 0 && (
                <div className="pt-5 border-t border-gray-100 dark:border-gray-700/50">
                    <div className="flex items-center justify-between mb-4">
                        <h4 className="text-xs font-black text-gray-400 uppercase tracking-widest">Pitch Arsenal Analysis</h4>
                    </div>
                    <div className="grid grid-cols-2 gap-x-6 gap-y-4">
                        {stats.slice(0, 4).map((s, i) => {
                            const totalPitches = stats.reduce((acc, curr) => acc + curr.pitch_count, 0);
                            const percentage = (s.pitch_count / totalPitches) * 100;
                            return (
                                <div key={i} className="space-y-1.5">
                                    <div className="flex justify-between text-[11px] font-black">
                                        <span className="text-gray-700 dark:text-gray-300">{s.pitch_name}</span>
                                        <span className="text-blue-500">{Math.round(percentage)}%</span>
                                    </div>
                                    <div className="h-2 w-full bg-gray-100 dark:bg-gray-900/50 rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-blue-500 rounded-full transition-all duration-1000 shadow-[0_0_8px_rgba(59,130,246,0.5)]"
                                            style={{ width: `${percentage}%` }}
                                        />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
};

export default MatchupAnalysisCard;
