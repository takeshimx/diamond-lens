import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import requests
import json
import os
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MLBKnowledgeRAG:
    """MLB用語集をRAGで検索・回答するサービス"""

    def __init__(self, vector_db_path: str = None):
        """
        Args:
            vector_db_path: ChromaDBの永続化パス
        """
        # デフォルトパスを絶対パスで設定
        if vector_db_path is None:
            project_root = Path(__file__).parent.parent.parent
            vector_db_path = str(project_root / "app" / "data" / "vector_db")

        logger.info(f"Initializing MLBKnowledgeRAG with vector_db_path: {vector_db_path}")

        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path=vector_db_path) # ベクトルDBをディスクに保存（サーバー再起動しても残る）

        # コレクション（テーブルのようなもの）の作成または取得
        self.collection = self.chroma_client.get_or_create_collection(
            name="mlb_metrics",
            metadata={
                "description": "MLB metrics and rules knowledge base"
            }
        )

        # Embeddingモデルの初期化（テキスト→ベクトル変換）
        logger.info("Loading sentence transformer model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("MLBKnowledgeRAG initialized successfully")
    

    def index_documents(self, documents: List[Dict[str, str]]) -> None:
        """
        Step 1: ドキュメントをベクトルDBにインデックス化
        
        Args:
            documents: ドキュメントリスト（document_loaderから取得）
        """

        if not documents:
            logger.warning("No documents to index")
            return
        
        logger.info(f"Indexing {len(documents)} documents...")

        for idx, doc in enumerate(documents):
            try:
                # encode document text to vector
                embedding = self.embedding_model.encode(doc["content"]).tolist()

                # add document to vector DB
                self.collection.add(
                    ids=[f"doc_{idx}_{doc['source']}"],
                    embeddings=[embedding],
                    documents=[doc["content"]],
                    metadatas=[{
                        "source": doc["source"],
                        "type": doc.get("type", "unknown")
                    }]
                )
                logger.info(f"Indexed: {doc['source']}")
            
            except Exception as e:
                logger.error(f"Error indexing document {idx}: {e}", exc_info=True)
                continue
        
        logger.info(f"Successfully indexed {len(documents)} documents")
    
    def search_knowledge(
        self,
        query: str,
        n_results: int = 3
    ) -> Dict[str, Any]:
        """
        Step 2: クエリに関連するドキュメントを検索
        
        Args:
            query: 検索クエリ
            n_results: 返す結果の数
            
        Returns:
            検索結果（documents, metadatas, distances）
        """
        logger.info(f"Searching for: {query}")

        # encode query to vector
        query_embedding = self.embedding_model.encode(query).tolist()

        # ベクトルDBで類似検索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        logger.info(f"Found {len(results['documents'][0])} results")
        return results
    
    def generate_answer_with_context(
        self,
        query: str,
        gemini_api_key: str,
        n_results: int = 3
    ) -> Dict[str, Any]:
        """
        Step 3: RAG 検索結果とLLMを組み合わせて回答生成
        
        Args:
            query: ユーザーの質問
            gemini_api_key: Gemini API キー
            n_results: 検索する関連ドキュメント数
            
        Returns:
            answer: LLMが生成した回答
            sources: 情報源のリスト
            context_used: 使用したコンテキスト
        """
        # Step 3-1: 関連ドキュメント検索
        search_results = self.search_knowledge(query, n_results)

        if not search_results['documents'][0]:
            logger.warning("No relevant documents found")
            return {
                "answer": "関連する情報が見つかりませんでした。",
                "sources": [],
                "context_used": []
            }
        
        # Step 3-2: 検索結果をコンテキストとして結合
        # 検索した複数のドキュメントを結合
        context_parts = []
        for idx, (doc, metadata) in enumerate(
            zip(search_results["documents"][0], search_results["metadatas"][0])
        ):
            context_parts.append(f"【情報源 {idx+1}: {metadata['source']}】\n{doc}")
        
        context = "\n\n".join(context_parts)
        logger.debug(f"Context length: {len(context)} characters")

        # Step 3-3: Gemini APIで回答生成
        prompt = f"""
        あなたはMLB野球の専門家です。以下の知識ベースを参考に、ユーザーの質問に日本語で回答してください。

        【重要な指示】
        - 知識ベースに記載されている情報のみを使用してください
        - 知識ベースにない情報は「情報がありません」と答えてください
        - 回答は簡潔かつ正確に

        【知識ベース】
        {context}

        【質問】
        {query}

        【回答】
        """
        
        GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        try:
            response = requests.post(
                GEMINI_API_URL, 
                headers=headers, 
                data=json.dumps(payload),
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            if result.get("candidates"):
                generated_text = result["candidates"][0]["content"]["parts"][0]["text"]
                
                # 情報源リストの作成
                sources = [
                    metadata["source"] 
                    for metadata in search_results["metadatas"][0]
                ]
                
                return {
                    "answer": generated_text,
                    "sources": list(set(sources)),  # 重複を除去
                    "context_used": context
                }
            else:
                logger.warning("No candidates in Gemini response")
                return {
                    "answer": "回答を生成できませんでした。",
                    "sources": [],
                    "context_used": context
                }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            return {
                "answer": f"APIエラーが発生しました: {str(e)}",
                "sources": [],
                "context_used": context
            }
        
        
