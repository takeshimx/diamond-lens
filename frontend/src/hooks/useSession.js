import { useState, useEffect } from 'react';

const SESSION_STORAGE_KEY = 'mlb_chat_session_id';

/**
 * チャットセッションIDを管理するフック。
 * localStorage との同期も担う。
 */
export const useSession = () => {
  const [sessionId, setSessionId] = useState(() =>
    localStorage.getItem(SESSION_STORAGE_KEY) || null
  );

  // sessionId が変わったら localStorage に保存
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
    }
  }, [sessionId]);

  const clearSession = () => {
    setSessionId(null);
    localStorage.removeItem(SESSION_STORAGE_KEY);
  };

  return { sessionId, setSessionId, clearSession };
};
