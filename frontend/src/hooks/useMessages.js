import { useState, useRef, useEffect } from 'react';

const INITIAL_MESSAGE = {
  id: 1,
  type: 'bot',
  content: 'こんにちは！MLBスタッツについて何でも聞いてください。選手の成績、チーム統計、歴史的データなど、お答えします！',
  timestamp: new Date(),
};

/**
 * チャットメッセージ・入力・ローディング状態を管理するフック。
 */
export const useMessages = () => {
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // メッセージが更新されるたびに最下部にスクロール
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const resetMessages = () => {
    setMessages([{ ...INITIAL_MESSAGE, timestamp: new Date() }]);
  };

  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString('ja-JP', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleVoiceTranscript = (transcript) => {
    setInputMessage(transcript);
  };

  return {
    messages,
    setMessages,
    inputMessage,
    setInputMessage,
    isLoading,
    setIsLoading,
    messagesEndRef,
    resetMessages,
    formatTime,
    handleVoiceTranscript,
  };
};
