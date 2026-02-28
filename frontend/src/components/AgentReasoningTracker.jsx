import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Brain, Wrench, CheckCircle, Circle, Clock } from 'lucide-react';

const AgentReasoningTracker = ({
    steps = [],
    isStreaming = false,
    isCollapsible = false
}) => {
    const [isExpanded, setIsExpanded] = useState(true);

    if (!steps || steps.length === 0) return null;

    const getStepIcon = (stepType, status) => {
        const iconProps = { className: "w-4 h-4 flex-shrink-0" };

        if (stepType === 'node_start' || stepType === 'node_end') {
            return status === 'completed'
                ? <CheckCircle {...iconProps} className="w-4 h-4 flex-shrink-0 text-green-500" />
                : <Circle {...iconProps} className="w-4 h-4 flex-shrink-0 text-blue-400 animate-pulse" />;
        }

        if (stepType === 'tool_call' || stepType === 'tool_result') {
            return <Wrench {...iconProps} className="w-4 h-4 flex-shrink-0 text-purple-400" />;
        }

        return <Brain {...iconProps} className="w-4 h-4 flex-shrink-0 text-gray-400" />;
    };

    const getStepColor = (node, status) => {
        if (status === 'completed') return 'text-green-600 dark:text-green-400';
        if (node === 'oracle') return 'text-blue-600 dark:text-blue-400';
        if (node === 'executor') return 'text-purple-600 dark:text-purple-400';
        if (node === 'synthesizer') return 'text-orange-600 dark:text-orange-400';
        return 'text-gray-600 dark:text-gray-400';
    };

    const formatTimestamp = (timestamp) => {
        if (!timestamp) return '';
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('ja-JP', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                fractionalSecondDigits: 1
            });
        } catch (e) {
            return '';
        }
    };

    return (
        <div className="mt-4 mb-4 p-4 bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800/50 dark:to-gray-800/30 rounded-xl border border-gray-200 dark:border-gray-600 shadow-sm">
            {/* ヘッダー */}
            <div
                className={`flex items-center justify-between mb-3 ${isCollapsible ? 'cursor-pointer' : ''}`}
                onClick={() => isCollapsible && setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-2">
                    <Brain className="w-5 h-5 text-purple-600 dark:text-purple-400 animate-pulse" />
                    <span className="text-sm font-bold uppercase tracking-wider text-purple-700 dark:text-purple-300">
                        AI推論プロセス
                    </span>
                    {isStreaming && (
                        <span className="ml-2 px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full animate-pulse">
                            実行中
                        </span>
                    )}
                </div>

                {isCollapsible && (
                    <button
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                        aria-label={isExpanded ? "折りたたむ" : "展開する"}
                    >
                        {isExpanded ? (
                            <ChevronUp className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                        ) : (
                            <ChevronDown className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                        )}
                    </button>
                )}
            </div>

            {/* ステップリスト */}
            {isExpanded && (
                <div className="space-y-2 relative">
                    {/* 縦線（タイムライン） */}
                    <div className="absolute left-[11px] top-2 bottom-2 w-0.5 bg-gradient-to-b from-blue-300 via-purple-300 to-orange-300 dark:from-blue-700 dark:via-purple-700 dark:to-orange-700 opacity-30" />

                    {steps.map((step, idx) => (
                        <div
                            key={idx}
                            className="relative flex items-start gap-3 pl-1 group transition-all duration-200 hover:translate-x-1"
                        >
                            {/* アイコン */}
                            <div className="relative z-10 bg-white dark:bg-gray-800 rounded-full p-0.5">
                                {getStepIcon(step.step_type, step.status)}
                            </div>

                            {/* ステップ詳細 */}
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                    {/* ノード名バッジ */}
                                    {step.node && (
                                        <span className={`px-2 py-0.5 text-xs font-semibold rounded-md ${getStepColor(step.node, step.status)} bg-white/50 dark:bg-gray-700/50`}>
                                            {step.node.toUpperCase()}
                                        </span>
                                    )}

                                    {/* メッセージ */}
                                    <span className="text-sm text-gray-700 dark:text-gray-300">
                                        {step.message}
                                    </span>

                                    {/* タイムスタンプ */}
                                    {step.timestamp && (
                                        <span className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
                                            <Clock className="w-3 h-3" />
                                            {formatTimestamp(step.timestamp)}
                                        </span>
                                    )}
                                </div>

                                {/* 詳細情報 */}
                                {step.detail && (
                                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 italic">
                                        {step.detail}
                                    </p>
                                )}

                                {/* ツールの出力サマリー */}
                                {step.output_summary && (
                                    <p className="mt-1 text-xs text-green-600 dark:text-green-400 font-medium">
                                        → {step.output_summary}
                                    </p>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* 折りたたまれている場合のサマリー */}
            {!isExpanded && (
                <div className="text-xs text-gray-500 dark:text-gray-400">
                    {steps.length}ステップ完了
                </div>
            )}
        </div>
    );
};

export default AgentReasoningTracker;
