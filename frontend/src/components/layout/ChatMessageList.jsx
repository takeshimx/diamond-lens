import { Bot, User, AlertTriangle, ThumbsUp, ThumbsDown } from 'lucide-react';
import AgentReasoningTracker from '../AgentReasoningTracker.jsx';
import SimpleChatChart from '../ChatChart.jsx';
import StatCard from '../chat/StatCard.jsx';
import DataTable from '../chat/DataTable.jsx';
import MatchupAnalysisCard from '../MatchupAnalysisCard.jsx';
import StrategyReportCard from '../StrategyReportCard.jsx';
import { FAILURE_CATEGORY_LABELS } from '../../constants/failureCategories.js';

const ChatMessageList = ({
  messages,
  feedbackState,
  activeFeedbackForm,
  feedbackFormData,
  setFeedbackFormData,
  setActiveFeedbackForm,
  handleFeedback,
  messagesEndRef,
  formatTime,
}) => (
  <div className="px-4 sm:px-6 py-4 space-y-4 h-full">
    {messages.map((message) => (
      <div
        key={message.id}
        className={`flex gap-3 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
      >
        {/* ボットアバター */}
        {message.type === 'bot' && (
          <div className="w-8 h-8 rounded-full bg-blue-600 dark:bg-blue-500 flex items-center justify-center flex-shrink-0 transition-colors duration-200">
            <Bot className="w-5 h-5 text-white" />
          </div>
        )}

        {/* メッセージ本体 */}
        <div className={`${message.isChart ? 'max-w-full lg:max-w-5xl' : 'max-w-full sm:max-w-2xl'} ${message.type === 'user' ? 'order-2' : ''}`}>
          <div
            className={`px-4 py-3 rounded-lg transition-colors duration-200 ${message.type === 'user'
              ? 'bg-blue-600 dark:bg-blue-500 text-white'
              : 'bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white'
              }`}
          >
            {/* ストリーミングステータス */}
            {message.isStreaming && message.streamingStatus && (
              <div className="mb-3 flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 italic">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-blue-600 dark:bg-blue-400 rounded-full animate-bounce"></span>
                  <span className="w-2 h-2 bg-blue-600 dark:bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
                  <span className="w-2 h-2 bg-blue-600 dark:bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                </div>
                <span>{message.streamingStatus}</span>
              </div>
            )}

            {/* 品質警告バナー */}
            {message.qualityWarning?.has_warning && (
              <div className="mb-3 flex items-start gap-2 rounded-md bg-amber-50 dark:bg-amber-900/30 border border-amber-300 dark:border-amber-700 px-3 py-2 text-sm text-amber-800 dark:text-amber-300">
                <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>
                  類似の質問で精度が低かった事例があります。回答内容を慎重にご確認ください。
                  {message.qualityWarning.top_failure_category && (
                    <span className="ml-1 text-amber-600 dark:text-amber-400">
                      ({FAILURE_CATEGORY_LABELS[message.qualityWarning.top_failure_category] ?? message.qualityWarning.top_failure_category})
                    </span>
                  )}
                </span>
              </div>
            )}

            {/* メッセージテキスト */}
            {!message.isStrategyReport && (
              <div className="mb-2">
                <p className="whitespace-pre-wrap">{message.content}</p>
                {message.isStreaming && !message.content && (
                  <div className="flex gap-1 text-gray-400">
                    <span className="animate-pulse">●</span>
                    <span className="animate-pulse" style={{ animationDelay: '0.15s' }}>●</span>
                    <span className="animate-pulse" style={{ animationDelay: '0.3s' }}>●</span>
                  </div>
                )}
              </div>
            )}

            {/* ストリーミング中の戦略レポートプレースホルダー */}
            {message.isStrategyReport && message.isStreaming && !message.content && (
              <div className="mb-2 flex gap-1 text-gray-400">
                <span className="animate-pulse">●</span>
                <span className="animate-pulse" style={{ animationDelay: '0.15s' }}>●</span>
                <span className="animate-pulse" style={{ animationDelay: '0.3s' }}>●</span>
              </div>
            )}

            {/* 思考プロセス */}
            {message.steps && message.steps.length > 0 && (
              <AgentReasoningTracker
                steps={message.steps}
                isStreaming={message.isStreaming}
                isCollapsible={!message.isStreaming}
              />
            )}

            {/* テーブル表示 */}
            {message.isTable && message.tableData && message.columns && (
              <DataTable
                tableData={message.tableData}
                columns={message.columns}
                isTransposed={message.isTransposed}
                decimalColumns={message.decimalColumns}
                grouping={message.grouping}
              />
            )}

            {/* チャート表示 */}
            {message.isChart && message.chartData && message.chartConfig ? (
              <SimpleChatChart
                chartData={message.chartData}
                chartConfig={message.chartConfig}
                chartType={message.chartType}
              />
            ) : message.isChart ? (
              <div className="mt-4 p-4 bg-red-100 dark:bg-red-900 rounded-lg">
                <p className="text-red-800 dark:text-red-200">
                  Chart data missing: isChart={String(message.isChart)}, hasData={String(!!message.chartData)}, hasConfig={String(!!message.chartConfig)}
                </p>
              </div>
            ) : null}

            {/* 統計データカード */}
            {message.stats && <StatCard stats={message.stats} />}

            {/* 対戦分析カード */}
            {message.isMatchupCard && message.matchupData && (
              <MatchupAnalysisCard matchupData={message.matchupData} />
            )}

            {/* 戦略レポートカード */}
            {message.isStrategyReport && message.content && !message.isStreaming && (
              <StrategyReportCard finalAnswer={message.content} strategyData={message.strategyData} />
            )}

            {/* フィードバック UI */}
            {message.type === 'bot' && message.requestId && (
              <>
                <div className="mt-3 flex items-center justify-end gap-2 border-t border-gray-100 dark:border-gray-600 pt-2">
                  <span className="text-xs text-gray-400 dark:text-gray-500 mr-1">回答の評価:</span>
                  <button
                    onClick={() => handleFeedback(message.id, message.requestId, 'good')}
                    disabled={feedbackState[message.id] === 'loading' || feedbackState[message.id] === 'good' || feedbackState[message.id] === 'bad'}
                    className={`p-1.5 rounded-md transition-colors duration-200 ${feedbackState[message.id] === 'good'
                      ? 'text-green-600 bg-green-50 dark:bg-green-900/20'
                      : 'text-gray-400 hover:text-green-600 hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50'
                      }`}
                    title="正確な回答"
                  >
                    <ThumbsUp className={`w-4 h-4 ${feedbackState[message.id] === 'good' ? 'fill-current' : ''}`} />
                  </button>
                  <button
                    onClick={() => handleFeedback(message.id, message.requestId, 'bad')}
                    disabled={feedbackState[message.id] === 'loading' || feedbackState[message.id] === 'good' || feedbackState[message.id] === 'bad'}
                    className={`p-1.5 rounded-md transition-colors duration-200 ${feedbackState[message.id] === 'bad'
                      ? 'text-red-600 bg-red-50 dark:bg-red-900/20'
                      : 'text-gray-400 hover:text-red-600 hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50'
                      }`}
                    title="不正確な回答/改善が必要"
                  >
                    <ThumbsDown className={`w-4 h-4 ${feedbackState[message.id] === 'bad' ? 'fill-current' : ''}`} />
                  </button>
                  {feedbackState[message.id] === 'error' && (
                    <span className="text-xs text-red-500 ml-1">送信失敗</span>
                  )}
                </div>

                {/* 詳細フィードバック入力パネル */}
                {activeFeedbackForm && String(activeFeedbackForm.messageId) === String(message.id) && (
                  <div
                    className="mt-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800"
                    style={{ display: 'block', width: '100%', position: 'relative', zIndex: 10 }}
                  >
                    <h4 className="text-xs font-bold text-yellow-800 dark:text-yellow-200 mb-2">改善のための詳細</h4>

                    <div className="flex flex-wrap gap-2 mb-3">
                      {[
                        { id: 'inaccurate', label: '不正確・誤り' },
                        { id: 'slow', label: '応答が遅い' },
                        { id: 'irrelevant', label: '無関係な回答' },
                        { id: 'wrong_player', label: '選手が違う' },
                        { id: 'wrong_stats', label: '統計が違う' },
                      ].map(cat => (
                        <button
                          key={cat.id}
                          onClick={() => setFeedbackFormData(prev => ({ ...prev, category: cat.id }))}
                          className={`px-2 py-1.5 text-xs rounded border transition-colors ${feedbackFormData.category === cat.id
                            ? 'bg-blue-600 border-blue-600 text-white shadow-sm'
                            : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-100 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-600'
                            }`}
                        >
                          {cat.label}
                        </button>
                      ))}
                    </div>

                    <textarea
                      value={feedbackFormData.reason}
                      onChange={(e) => setFeedbackFormData(prev => ({ ...prev, reason: e.target.value }))}
                      placeholder="具体的な問題点（任意）"
                      className="w-full p-2 text-xs bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-md mb-3 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:text-white dark:placeholder-gray-500"
                      rows="2"
                    />

                    <div className="flex justify-end gap-2 font-medium">
                      <button
                        onClick={() => setActiveFeedbackForm(null)}
                        className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                      >
                        キャンセル
                      </button>
                      <button
                        onClick={() => handleFeedback(message.id, message.requestId, 'bad', feedbackFormData)}
                        disabled={!feedbackFormData.category}
                        className="px-4 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
                      >
                        送信する
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* タイムスタンプ */}
          <p className={`text-xs text-gray-500 dark:text-gray-400 mt-1 transition-colors duration-200 ${message.type === 'user' ? 'text-right' : 'text-left'}`}>
            {formatTime(message.timestamp)}
          </p>
        </div>

        {/* ユーザーアバター */}
        {message.type === 'user' && (
          <div className="w-8 h-8 rounded-full bg-gray-600 dark:bg-gray-500 flex items-center justify-center flex-shrink-0 order-3 transition-colors duration-200">
            <User className="w-5 h-5 text-white" />
          </div>
        )}
      </div>
    ))}

    <div ref={messagesEndRef} />
  </div>
);

export default ChatMessageList;
