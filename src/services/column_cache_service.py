"""
Column cache service for caching project columns
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.api.ticktick_client import TickTickClient
from src.utils.logger import logger
from src.config.constants import TICKTICK_API_VERSION


class ColumnCacheService:
    """Service for caching project columns with TTL"""
    
    def __init__(self, ticktick_client: TickTickClient):
        """
        Initialize column cache service
        
        Args:
            ticktick_client: TickTick API client
        """
        self.client = ticktick_client
        self.logger = logger
        # Cache structure: {project_id: {"columns": [...], "last_update": datetime}}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl: timedelta = timedelta(hours=1)  # 1 час (колонки меняются реже)
    
    async def get_columns(self, project_id: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get list of columns for a project (with caching)
        
        Args:
            project_id: Project ID
            force_refresh: Force cache refresh
        
        Returns:
            List of columns
        """
        if force_refresh or self._should_refresh(project_id):
            self.logger.debug(f"[ColumnCache] Refreshing columns cache for project {project_id}...")
            try:
                # Get project data which includes columns
                project_data = await self.client.get(
                    endpoint=f"/open/{TICKTICK_API_VERSION}/project/{project_id}/data",
                    headers=self.client._get_headers(),
                )
                
                columns = project_data.get('columns', []) if isinstance(project_data, dict) else []
                
                self._cache[project_id] = {
                    "columns": columns,
                    "last_update": datetime.now()
                }
                
                self.logger.debug(f"[ColumnCache] Columns cache refreshed for project {project_id}: {len(columns)} columns")
            except Exception as e:
                self.logger.error(f"[ColumnCache] Failed to refresh columns cache for project {project_id}: {e}", exc_info=True)
                # Return cached columns if available, even if stale
                if project_id in self._cache and self._cache[project_id].get("columns"):
                    self.logger.warning(f"[ColumnCache] Using stale cache for project {project_id} due to refresh error")
                    return self._cache[project_id]["columns"]
                # Return empty list if no cache
                return []
        else:
            cached_columns = self._cache.get(project_id, {}).get("columns", [])
            self.logger.debug(f"[ColumnCache] Using cached columns for project {project_id} ({len(cached_columns)} columns)")
        
        return self._cache.get(project_id, {}).get("columns", [])
    
    async def find_column_by_name(
        self, 
        project_id: str, 
        column_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find column by name (case-insensitive, partial match)
        
        Args:
            project_id: Project ID
            column_name: Column name to search for
        
        Returns:
            Column dict if found, None otherwise
        """
        columns = await self.get_columns(project_id)
        
        if not columns:
            self.logger.debug(f"[ColumnCache] No columns found for project {project_id}")
            return None
        
        column_name_lower = column_name.lower().strip()
        
        # First, try exact match (case-insensitive)
        for column in columns:
            if column.get('name', '').lower().strip() == column_name_lower:
                self.logger.debug(f"[ColumnCache] Exact match found: '{column.get('name')}' (ID: {column.get('id')})")
                return column
        
        # Then, try partial match (contains)
        for column in columns:
            column_name_clean = column.get('name', '').lower().strip()
            if column_name_lower in column_name_clean or column_name_clean in column_name_lower:
                self.logger.debug(f"[ColumnCache] Partial match found: '{column.get('name')}' (ID: {column.get('id')})")
                return column
        
        self.logger.warning(
            f"[ColumnCache] Column '{column_name}' not found in project {project_id}. "
            f"Available columns: {[c.get('name', '') for c in columns]}"
        )
        return None
    
    def _should_refresh(self, project_id: str) -> bool:
        """
        Check if cache should be refreshed for a project
        
        Args:
            project_id: Project ID
        
        Returns:
            True if cache should be refreshed
        """
        if project_id not in self._cache:
            return True
        
        cache_entry = self._cache[project_id]
        if not cache_entry.get("last_update"):
            return True
        
        time_since_update = datetime.now() - cache_entry["last_update"]
        should_refresh = time_since_update > self._cache_ttl
        
        if should_refresh:
            self.logger.debug(
                f"[ColumnCache] Cache expired for project {project_id}: "
                f"last update was {time_since_update.total_seconds() / 60:.1f} minutes ago, "
                f"TTL is {self._cache_ttl.total_seconds() / 60:.1f} minutes"
            )
        
        return should_refresh
    
    def clear_cache(self, project_id: Optional[str] = None):
        """
        Clear columns cache
        
        Args:
            project_id: If provided, clear cache only for this project. Otherwise, clear all.
        """
        if project_id:
            if project_id in self._cache:
                del self._cache[project_id]
                self.logger.debug(f"[ColumnCache] Cache cleared for project {project_id}")
        else:
            self._cache = {}
            self.logger.debug("[ColumnCache] All cache cleared")



