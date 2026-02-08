import json
import redis
import os
import logging

logger = logging.getLogger(__name__)


class StatsCache:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD", None),
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5
        )

        self.ttl = int(os.getenv("CACHE_TTL", 3600))


    def _get_cache_key(self, player_name: str, season: int, query_type: str) -> str:
        """
        Generate cache key for a given player and query.
        """
        return f"stats:{player_name}:{season}:{query_type}"


    def get_player_stats(self, player_name: str, season: int, query_type: str):
        """
        """
        key = self._get_cache_key(player_name, season, query_type)
        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
        except redis.exceptions.ConnectionError:
            logger.warning(f"⚠️ Redis connection failed when getting stats for {player_name}, season {season}, query {query_type}. Proceeding without cache.")
        except Exception as e:
            logger.error(f"❌ Unexpected error getting stats from cache: {e}")
        
        return None
        

    def set_player_stats(self, player_name: str, season: int, query_type: str, data: dict):

        key = self._get_cache_key(player_name, season, query_type)

        # save stats to cache
        try:
            self.redis_client.setex(
                key,
                self.ttl,
                json.dumps(data)
            )
        except redis.exceptions.ConnectionError:
            logger.warning(f"⚠️ Redis connection failed when setting stats for {player_name}, season {season}, query {query_type}. Proceeding without cache.")
        except Exception as e:
            logger.error(f"❌ Unexpected error setting stats to cache: {e}")