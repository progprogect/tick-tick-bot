"""
Project cache service for caching project list
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.api.ticktick_client import TickTickClient
from src.utils.logger import logger


class ProjectCacheService:
    """Service for caching project list with TTL"""
    
    def __init__(self, ticktick_client: TickTickClient):
        """
        Initialize project cache service
        
        Args:
            ticktick_client: TickTick API client
        """
        self.client = ticktick_client
        self.logger = logger
        self._projects: List[Dict[str, Any]] = []
        self._last_update: Optional[datetime] = None
        self._cache_ttl: timedelta = timedelta(hours=24)  # 24 часа
    
    async def get_projects(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get list of projects (with caching)
        
        Args:
            force_refresh: Force cache refresh
        
        Returns:
            List of projects
        """
        if force_refresh or self._should_refresh():
            self.logger.info("[ProjectCache] Refreshing projects cache...")
            try:
                self._projects = await self.client.get_projects()
                self._last_update = datetime.now()
                self.logger.info(f"[ProjectCache] Projects cache refreshed: {len(self._projects)} projects")
            except Exception as e:
                self.logger.error(f"[ProjectCache] Failed to refresh projects cache: {e}", exc_info=True)
                # Return cached projects if available, even if stale
                if self._projects:
                    self.logger.warning("[ProjectCache] Using stale cache due to refresh error")
                    return self._projects
                raise
        else:
            self.logger.debug(f"[ProjectCache] Using cached projects ({len(self._projects)} projects)")
        
        return self._projects
    
    def _should_refresh(self) -> bool:
        """
        Check if cache should be refreshed
        
        Returns:
            True if cache should be refreshed
        """
        if not self._projects or not self._last_update:
            return True
        
        time_since_update = datetime.now() - self._last_update
        should_refresh = time_since_update > self._cache_ttl
        
        if should_refresh:
            self.logger.debug(
                f"[ProjectCache] Cache expired: "
                f"last update was {time_since_update.total_seconds() / 3600:.1f} hours ago, "
                f"TTL is {self._cache_ttl.total_seconds() / 3600:.1f} hours"
            )
        
        return should_refresh
    
    def clear_cache(self):
        """Clear projects cache"""
        self._projects = []
        self._last_update = None
        self.logger.debug("[ProjectCache] Cache cleared")







