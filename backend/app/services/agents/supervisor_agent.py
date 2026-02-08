import os
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Literal


class SupervisorAgent:
    """
    Supervisor agent that routes queries to specialized agents.
    """

    def __init__(self):
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GEMINI_API_KEY_V2"),
            temperature=0.0 # Deterministic routing
        )
    

    def route_query(self, query: str) -> Literal["stats", "matchup", "prediction"]:
        """
        Analyze query and route to appropriate agent.
        
        Args:
            query: User's natural language question
            
        Returns:
            Agent type: "stats", "matchup", or "prediction"
        """

        routing_prompt = f"""
        あなたは野球統計システムのルーティング担当です。
ユーザーの質問を分析し、適切なエージェントを選択してください。
エージェントの種類:
- stats: 通常の成績（打率、本塁打数、防御率など）
- matchup: 対戦成績（特定の打者vs投手）
- prediction: 予測（次の試合の結果、今シーズンの成績予想など）
質問: {query}
以下のいずれかを返してください: stats, matchup, prediction
        """

        response = self.model.invoke(routing_prompt)
        agent_type = response.content.strip().lower()

        # Validation
        if agent_type not in ["stats", "matchup", "prediction"]:
            # Default to stats if unclear
            return "stats"
        
        return agent_type

