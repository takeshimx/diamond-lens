from typing import List, Dict, Any, Optional
# from llama_index.core.memory import ChatMemoryBuffer
# from llama_index.llms.gemini import Gemini
import redis
import json
import logging
from datetime import datetime
import os
import requests

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managging conversations using Redis as the backend."""

    def __init__(self):
        # Intitialize redis client
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD", None),
            decode_responses=True,
            socket_connect_timeout=0.5, # 接続タイムアウトを短縮
            socket_timeout=0.5          # 通信タイムアウトを短縮
        )

        # TTL
        self.ttl = int(os.getenv("CHAT_HISTORY_TTL", 3600))

        # Gemini API Key (requests方式で使用)
        self.gemini_api_key = os.getenv("GEMINI_API_KEY_V2")

        # LlamaIndex版（将来使用する可能性あり）
        # self.llm = Gemini(
        #     model="models/gemini-2.5-flash",
        #     api_key=os.getenv("GEMINI_API_KEY_V2")
        # )
    
    # Helper method to generate Redis key
    def _get_session_key(self, session_id: str) -> str:
        """
        Generate Redis key for a given session ID

        例: session_id="abc123" → "chat_history:abc123"
        """
        return f"chat_history:{session_id}"
    

    # Method to get chat history
    def get_chat_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Retrieve chat history for a given session ID.
        
        Args:
            session_id (str): The session ID.
            
        Returns:
            会話履歴のリスト（JSON形式）
            例: [{"role": "user", "content": "大谷の成績は？"}, ...]
        """
        key = self._get_session_key(session_id)
        try:
            history_json = self.redis_client.get(key)
            if history_json:
                return json.loads(history_json)
        except redis.exceptions.ConnectionError:
            logger.warning(f"⚠️ Redis connection failed when getting history for session {session_id}. Proceeding with empty context.")
        except Exception as e:
            logger.error(f"❌ Unexpected error getting chat history: {e}")
            
        return []
    
    def add_message(
            self,
            session_id: str,
            role: str, # 'user' or 'assistant'
            content: str, # メッセージ内容
            metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a message to the chat history for a given session ID.
        
        Args:
            session_id (str): The session ID.
            role (str): The role of the message sender ('user' or 'assistant').
            content (str): The message content.
            metadata (Optional[Dict[str, Any]]): Additional metadata for the message. （例: {"player_name": "大谷翔平", "query_type": "batting"}）
        """
        key = self._get_session_key(session_id)
        history = self.get_chat_history(session_id)

        # Create new message entry
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        history.append(message)

        # Save updated history back to Redis only 10 latest messages
        trimmed_history = history[-10:]
        try:
            self.redis_client.setex(
                key,
                self.ttl,
                json.dumps(trimmed_history, ensure_ascii=False) # JSON文字列化（日本語対応）
            )
        except redis.exceptions.ConnectionError:
            logger.warning(f"⚠️ Redis connection failed when adding message for session {session_id}. History not saved.")
        except Exception as e:
            logger.error(f"❌ Unexpected error adding message to chat history: {e}")
    

    def resolve_context(
            self,
            current_query: str,
            session_id: str
    ) -> Dict[str, Any]:
        """
        Resolve context by referencing chat history.
        会話履歴から代名詞や省略された情報を解決
        
        例:
            履歴: "大谷翔平の2024年成績は？"
            現在: "彼のRISP打率は？"
            結果: "大谷翔平のRISP打率は？"（"彼"を解決）
        
        Returns:
            Returns:
            {
                "resolved_query": "完全な質問文",
                "player_name": "大谷翔平",
                "season": 2024,
                "context_used": True
            }
        """
        history = self.get_chat_history(session_id)

        if not history:
            return {"resolved_query": current_query, "context_used": False}
        
        # Convert history to text for LLM input （会話履歴をテキスト形式に変換）
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}" for msg in history[-5:] # 直近5件のみ使用
        ])

        # Prepare prompt for LLM
        prompt = f"""
        あなたは会話の文脈を理解するアシスタントです。

        # 会話履歴
        {history_text}

        # 現在のユーザー質問
        {current_query}

        # タスク
        もし現在の質問に代名詞（彼、彼女、その選手など）や省略された情報がある場合、
        会話履歴から補完して完全な質問に書き換えてください。

        省略がない場合は、そのまま返してください。

        # 出力形式（JSON）
        {{
            "resolved_query": "完全な質問文",
            "player_name": "言及されている選手名（あれば）",
            "season": "言及されているシーズン（あれば）",
            "context_used": true/false
        }}
        """

        try:
            # Call Gemini API (requests方式)
            GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            }

            response = requests.post(GEMINI_API_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result_json = response.json()

            if result_json.get("candidates"):
                json_string = result_json["candidates"][0]["content"]["parts"][0]["text"]
                result = json.loads(json_string)
                logger.info(f"✅ Context resolved: '{current_query}' → '{result['resolved_query']}'")
                return result

            return {"resolved_query": current_query, "context_used": False}

            # LlamaIndex版（将来使用する可能性あり）
            # response = self.llm.complete(prompt)
            # result = json.loads(response.text)
            # logger.info(f"Context resolved: '{current_query}' → '{result['resolved_query']}'")
            # return result

        except Exception as e:
            logger.error(f"❌ Context resolution failed: {e}")
            return {
                "resolved_query": current_query,
                "context_used": False
            }
    
    def clear_session(self, session_id: str):
        """
        Clear chat history for a given session ID.
        
        用途:
            - ユーザーが「会話をリセット」ボタンを押した時
            - テストのクリーンアップ
        """
        key = self._get_session_key(session_id)
        try:
            self.redis_client.delete(key)
            logger.info(f"Session cleared: {session_id}")
        except redis.exceptions.ConnectionError:
            logger.warning(f"⚠️ Redis connection failed when clearing session {session_id}.")
        except Exception as e:
            logger.error(f"❌ Unexpected error clearing session: {e}")
    

_conversation_service = None

def get_conversation_service() -> ConversationService:
    """
    Get singleton instance of ConversationService.
    
    理由: Redis接続を使い回す（毎回接続すると遅い）
    """
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service


