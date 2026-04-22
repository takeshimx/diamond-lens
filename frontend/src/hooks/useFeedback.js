import { useState } from 'react';

/**
 * フィードバック送信・状態管理フック。
 *
 * @param {object} deps
 * @param {Function} deps.getBackendURL
 * @param {Function} deps.getAuthHeaders
 * @param {string|null} deps.sessionId
 */
export const useFeedback = ({ getBackendURL, getAuthHeaders, sessionId }) => {
  const [feedbackState, setFeedbackState] = useState({});
  const [activeFeedbackForm, setActiveFeedbackForm] = useState(null); // { messageId, requestId, rating }
  const [feedbackFormData, setFeedbackFormData] = useState({ category: '', reason: '' });

  const handleFeedback = async (messageId, requestId, rating, details = null) => {
    if (!requestId || !sessionId) {
      console.warn("フィードバックを送信できません: request_id または session_id が不足しています", { requestId, sessionId });
      return;
    }

    // 「Bad」評価かつ詳細がまだ入力されていない場合は、入力フォームを表示する
    if (rating === 'bad' && !details) {
      setActiveFeedbackForm({ messageId, requestId, rating });
      setFeedbackFormData({ category: '', reason: '' });
      return;
    }

    // すでにフィードバック送信中の場合はスキップ
    if (feedbackState[messageId] === 'loading') return;

    setFeedbackState(prev => ({ ...prev, [messageId]: 'loading' }));

    try {
      const baseURL = getBackendURL();
      const endpoint = `${baseURL}/api/v1/qa/feedback`;

      const requestBody = {
        session_id: sessionId,
        request_id: requestId,
        user_rating: rating,
        category: details?.category || null,
        reason: details?.reason || null,
      };

      const headers = await getAuthHeaders();
      const response = await fetch(endpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`Feedback failed: ${response.status}`);
      }

      console.log('✅ デバッグ：フィードバック送信成功', rating, details);
      setFeedbackState(prev => ({ ...prev, [messageId]: rating }));
      setActiveFeedbackForm(null);
    } catch (error) {
      console.error('❌ デバッグ：フィードバック送信エラー:', error);
      setFeedbackState(prev => ({ ...prev, [messageId]: 'error' }));
    }
  };

  return {
    feedbackState,
    activeFeedbackForm,
    setActiveFeedbackForm,
    feedbackFormData,
    setFeedbackFormData,
    handleFeedback,
  };
};
