import os
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Literal
from backend.app.config.prompt_registry import get_prompt, get_prompt_version


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
    

    def route_query(self, query: str) -> Literal["batter", "pitcher", "stats", "matchup", "prediction"]:
        """
        Analyze query and route to appropriate agent.
        
        Args:
            query: User's natural language question
            
        Returns:
            Agent type: "stats", "matchup", or "prediction"
        """

        routing_prompt = get_prompt("routing", query=query)
        logger.info(f"Using routing prompt version: {get_prompt_version('routing')}")

        response = self.model.invoke(routing_prompt)
        agent_type = response.content.strip().lower()

        # Validation
        if agent_type not in ["batter", "pitcher", "stats", "matchup", "prediction"]:
            # Default to stats if unclear
            return "stats"
        
        return agent_type

