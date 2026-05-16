import os
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Literal
from backend.app.config.prompt_registry import get_prompt, get_prompt_version
from backend.app.services.llm_gateway_service import LangchainUsageCallback
from backend.app.utils.structured_logger import get_logger

logger = get_logger("supervisor-agent")


class SupervisorAgent:
    """
    Supervisor agent that routes queries to specialized agents.
    """

    def __init__(self):
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GEMINI_API_KEY_V2"),
            temperature=0.0, # Deterministic routing
            callbacks=[LangchainUsageCallback(feature="supervisor_agent", model="gemini-2.5-flash")],
        )
    

    def route_query(self, query: str, role: str = "active") -> Literal["batter", "pitcher", "stats", "matchup", "strategy"]:
        """
        Analyze query and route to appropriate agent.

        Args:
            query: User's natural language question
            role: "active"（本番）または "shadow"（シャドー評価用）。
                  shadow 指定時は SHADOW_VERSIONS["routing"] のプロンプトを使用する。

        Returns:
            Agent type: "batter", "pitcher", "stats", or "matchup"
        """

        routing_prompt = get_prompt("routing", role=role, query=query)
        logger.info(f"Using routing prompt version: {get_prompt_version('routing', role=role)} role={role}")

        response = self.model.invoke(routing_prompt)
        agent_type = response.content.strip().lower()

        # Validation
        if agent_type not in ["batter", "pitcher", "stats", "matchup", "strategy"]:
            return "stats"

        return agent_type

