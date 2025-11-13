"""
Smart router with operation grouping and composite command support
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from src.api.ticktick_client import TickTickClient
from src.models.command import (
    ParsedCommand,
    Operation,
    ActionType,
    TaskIdentifier,
    FieldModifier,
)
from src.services.task_manager import TaskManager
from src.services.task_modifier import TaskModifier
from src.services.tag_manager import TagManager
from src.services.note_manager import NoteManager
from src.services.task_cache import TaskCacheService
from src.services.project_cache_service import ProjectCacheService
from src.services.task_search_service import TaskSearchService
from src.services.recurring_task_manager import RecurringTaskManager
from src.services.reminder_manager import ReminderManager
from src.services.batch_processor import BatchProcessor
from src.services.analytics_service import AnalyticsService
from src.utils.logger import logger


class OperationGroup:
    """Group of operations of the same type"""
    
    def __init__(self, operation_type: ActionType):
        self.type = operation_type
        self.operations: List[Operation] = []
        self.requires_current_data = False
    
    def add_operation(self, operation: Operation):
        """Add operation to group"""
        self.operations.append(operation)
        if operation.requires_current_data:
            self.requires_current_data = True


class SmartRouter:
    """Smart router with operation grouping and composite command support"""
    
    def __init__(
        self,
        ticktick_client: TickTickClient,
        task_manager: TaskManager,
        task_modifier: TaskModifier,
        tag_manager: TagManager,
        note_manager: NoteManager,
        recurring_task_manager: RecurringTaskManager,
        reminder_manager: ReminderManager,
        batch_processor: BatchProcessor,
        analytics_service: AnalyticsService,
    ):
        """
        Initialize smart router
        
        Args:
            ticktick_client: TickTick API client
            task_manager: Task manager
            task_modifier: Task modifier
            tag_manager: Tag manager
            note_manager: Note manager
            recurring_task_manager: Recurring task manager
            reminder_manager: Reminder manager
            batch_processor: Batch processor
            analytics_service: Analytics service
        """
        self.client = ticktick_client
        self.task_manager = task_manager
        self.task_modifier = task_modifier
        self.tag_manager = tag_manager
        self.note_manager = note_manager
        self.recurring_task_manager = recurring_task_manager
        self.reminder_manager = reminder_manager
        self.batch_processor = batch_processor
        self.analytics_service = analytics_service
        self.cache = TaskCacheService()
        self.project_cache = ProjectCacheService(ticktick_client)
        self.task_search = TaskSearchService(ticktick_client, self.cache, self.project_cache)
        self.logger = logger
    
    async def route(self, command: ParsedCommand) -> str:
        """
        Route command (supports both old and new formats)
        
        Args:
            command: ParsedCommand (can be composite or old format)
            
        Returns:
            Response message
        """
        # Check if composite command
        if command.is_composite():
            return await self._route_composite(command)
        else:
            # Old format - convert to single operation and route
            return await self._route_legacy(command)
    
    async def _route_composite(self, command: ParsedCommand) -> str:
        """
        Route composite command with multiple operations
        
        Args:
            command: Composite ParsedCommand
            
        Returns:
            Combined response message
        """
        if not command.operations:
            raise ValueError("No operations in composite command")
        
        # 1. Group operations by type (merge same-type operations)
        grouped = self._group_operations(command.operations)
        
        # 2. Resolve task identifiers if needed
        context = await self._resolve_context(command, grouped)
        
        # 3. Execute groups sequentially
        results = []
        errors = []
        
        for group in grouped:
            try:
                result = await self._execute_group(group, context)
                results.append(result)
            except Exception as e:
                error_msg = f"Операция '{group.type.value}' не выполнена: {str(e)}"
                errors.append(error_msg)
                self.logger.warning(f"Operation failed: {error_msg}")
                # Continue with other operations
        
        # 4. Format response
        if errors:
            success_msg = f"✓ Выполнено: {len(results)} операций"
            error_msg = f"Ошибки: {', '.join(errors)}"
            return f"{success_msg}. {error_msg}. Попробуйте выполнить проблемные операции отдельно."
        
        return self._combine_results(results)
    
    def _group_operations(self, operations: List[Operation]) -> List[OperationGroup]:
        """
        Group operations by type (merge same-type operations)
        
        Args:
            operations: List of operations
            
        Returns:
            List of operation groups
        """
        groups: Dict[ActionType, OperationGroup] = {}
        
        for operation in operations:
            op_type = operation.type
            
            # For update_task operations, we can merge modifications
            if op_type == ActionType.UPDATE_TASK:
                if op_type not in groups:
                    groups[op_type] = OperationGroup(op_type)
                groups[op_type].add_operation(operation)
            else:
                # For other operations, keep separate
                if op_type not in groups:
                    groups[op_type] = OperationGroup(op_type)
                groups[op_type].add_operation(operation)
        
        return list(groups.values())
    
    async def _resolve_context(
        self,
        command: ParsedCommand,
        groups: List[OperationGroup],
    ) -> Dict[str, Any]:
        """
        Resolve task identifiers and prepare context
        
        Args:
            command: ParsedCommand
            groups: Operation groups
            
        Returns:
            Context dictionary
        """
        context = {}
        
        # Resolve common task identifier if present
        if command.task_identifier:
            task_id = await self._resolve_task_identifier(command.task_identifier)
            context['task_id'] = task_id
            context['task_identifier'] = command.task_identifier
        
        # Resolve task identifiers for operations that need them
        for group in groups:
            for operation in group.operations:
                if operation.task_identifier:
                    task_id = await self._resolve_task_identifier(operation.task_identifier)
                    context[f'operation_{id(operation)}_task_id'] = task_id
                
                if operation.requires_current_data:
                    # Get task_id for this operation
                    task_id = context.get('task_id')
                    if not task_id and operation.task_identifier:
                        task_id = await self._resolve_task_identifier(operation.task_identifier)
                    
                    if task_id:
                        current_data = self.cache.get_task_data(task_id)
                        context[f'operation_{id(operation)}_current_data'] = current_data or {}
        
        return context
    
    async def _resolve_task_identifier(self, identifier: TaskIdentifier) -> str:
        """
        Resolve task identifier to task ID
        
        Args:
            identifier: TaskIdentifier
            
        Returns:
            Task ID
        """
        if identifier.type == "id":
            return identifier.value
        elif identifier.type == "title":
            # Use TaskSearchService to find task
            task = await self.task_search.find_task_by_title(
                title=identifier.value,
                project_id=None,
            )
            
            if task:
                return task.get("id")
            
            raise ValueError(f"Задача '{identifier.value}' не найдена")
        else:
            raise ValueError(f"Unknown identifier type: {identifier.type}")
    
    async def _execute_group(
        self,
        group: OperationGroup,
        context: Dict[str, Any],
    ) -> str:
        """
        Execute operation group
        
        Args:
            group: OperationGroup
            context: Context dictionary
            
        Returns:
            Result message
        """
        if group.type == ActionType.UPDATE_TASK:
            # Handle update_task - can be single task (merged) or multiple tasks
            return await self._execute_unified_update(group, context)
        elif group.type == ActionType.CREATE_TASK:
            # Execute all create operations
            results = []
            for operation in group.operations:
                result = await self._execute_create_task(operation, context)
                results.append(result)
            return self._combine_results(results)
        elif group.type == ActionType.DELETE_TASK:
            # Execute all delete operations
            results = []
            for operation in group.operations:
                result = await self._execute_delete_task(operation, context)
                results.append(result)
            return self._combine_results(results)
        elif group.type == ActionType.MOVE_TASK:
            # Execute all move operations
            results = []
            for operation in group.operations:
                result = await self._execute_move_task(operation, context)
                results.append(result)
            return self._combine_results(results)
        elif group.type == ActionType.BULK_MOVE:
            # Bulk operations are single by nature
            return await self._execute_bulk_move(group.operations[0], context)
        elif group.type == ActionType.ADD_TAGS:
            # Execute all add_tags operations
            results = []
            for operation in group.operations:
                result = await self._execute_add_tags(operation, context)
                results.append(result)
            return self._combine_results(results)
        elif group.type == ActionType.ADD_NOTE:
            # Execute all add_note operations
            results = []
            for operation in group.operations:
                result = await self._execute_add_note(operation, context)
                results.append(result)
            return self._combine_results(results)
        elif group.type == ActionType.CREATE_RECURRING_TASK:
            # Execute all create_recurring_task operations
            results = []
            for operation in group.operations:
                result = await self._execute_create_recurring_task(operation, context)
                results.append(result)
            return self._combine_results(results)
        elif group.type == ActionType.SET_REMINDER:
            # Execute all set_reminder operations
            results = []
            for operation in group.operations:
                result = await self._execute_set_reminder(operation, context)
                results.append(result)
            return self._combine_results(results)
        elif group.type == ActionType.GET_ANALYTICS:
            # Analytics operations are single by nature
            return await self._execute_get_analytics(group.operations[0], context)
        elif group.type == ActionType.OPTIMIZE_SCHEDULE:
            # Optimize schedule operations are single by nature
            return await self._execute_optimize_schedule(group.operations[0], context)
        else:
            raise ValueError(f"Unknown operation type: {group.type}")
    
    async def _execute_unified_update(
        self,
        group: OperationGroup,
        context: Dict[str, Any],
    ) -> str:
        """
        Execute unified update_task - merge all modifications into one API call for single task,
        or execute separately for multiple different tasks
        
        Args:
            group: OperationGroup with update_task operations
            context: Context dictionary
            
        Returns:
            Result message
        """
        # Collect all task_ids from operations
        task_ids = set()
        operations_by_task = {}  # task_id -> list of operations
        
        for operation in group.operations:
            # Resolve task_id for this operation
            task_id = None
            if operation.task_identifier:
                task_id = context.get(f'operation_{id(operation)}_task_id')
                if not task_id:
                    # Try to resolve it now
                    try:
                        task_id = await self._resolve_task_identifier(operation.task_identifier)
                        context[f'operation_{id(operation)}_task_id'] = task_id
                    except Exception as e:
                        self.logger.warning(f"Failed to resolve task identifier for operation: {e}")
                        continue
            
            if not task_id:
                # Fallback to common task_id
                task_id = context.get('task_id')
            
            if not task_id:
                raise ValueError(f"Task ID not found for update operation: {operation.task_identifier}")
            
            task_ids.add(task_id)
            
            # Group operations by task_id
            if task_id not in operations_by_task:
                operations_by_task[task_id] = []
            operations_by_task[task_id].append(operation)
        
        if not task_ids:
            raise ValueError("No valid task IDs found for update operations")
        
        # If all operations are for the same task, merge modifications
        if len(task_ids) == 1:
            task_id = list(task_ids)[0]
            operations = operations_by_task[task_id]
            
            # Merge all modifications from all operations
            all_modifications = {}
            for operation in operations:
                if operation.modifications:
                    all_modifications.update(operation.modifications)
            
            if not all_modifications:
                raise ValueError("No modifications in update operations")
            
            # Use TaskModifier to apply all modifications
            first_op = operations[0]
            task_identifier = first_op.task_identifier.value if first_op.task_identifier else None
            return await self.task_modifier.modify_task(
                task_id=task_id,
                modifications=all_modifications,
                task_identifier=task_identifier,
            )
        else:
            # Multiple different tasks - execute each separately
            results = []
            for task_id, operations in operations_by_task.items():
                # Merge modifications for this specific task
                task_modifications = {}
                for operation in operations:
                    if operation.modifications:
                        task_modifications.update(operation.modifications)
                
                if not task_modifications:
                    continue
                
                # Execute update for this task
                first_op = operations[0]
                task_identifier = first_op.task_identifier.value if first_op.task_identifier else None
                result = await self.task_modifier.modify_task(
                    task_id=task_id,
                    modifications=task_modifications,
                    task_identifier=task_identifier,
                )
                results.append(result)
            
            if not results:
                raise ValueError("No valid update operations executed")
            
            return self._combine_results(results)
    
    async def _execute_create_task(
        self,
        operation: Operation,
        context: Dict[str, Any],
    ) -> str:
        """Execute create_task operation"""
        # Convert Operation to ParsedCommand for TaskManager
        from src.models.command import ParsedCommand
        command = ParsedCommand(
            action=ActionType.CREATE_TASK,
            title=operation.params.get("title"),
            project_id=operation.params.get("projectId"),
            due_date=operation.params.get("dueDate"),
            priority=operation.params.get("priority"),
            tags=operation.params.get("tags"),
            notes=operation.params.get("notes"),
            reminder=operation.params.get("reminder"),
        )
        
        result = await self.task_manager.create_task(command)
        
        # Update context with created task_id
        # Extract task_id from result or from cache
        if operation.params.get("title"):
            task_id = await self.task_search.find_task_id_by_title(operation.params.get("title"))
            if task_id:
                context['task_id'] = task_id
        
        return result
    
    async def _execute_delete_task(
        self,
        operation: Operation,
        context: Dict[str, Any],
    ) -> str:
        """Execute delete_task operation"""
        # Prefer operation-specific task_id for multiple operations support
        task_id = None
        if operation.task_identifier:
            task_id = context.get(f'operation_{id(operation)}_task_id')
            if not task_id:
                # Try to resolve it now
                try:
                    task_id = await self._resolve_task_identifier(operation.task_identifier)
                    context[f'operation_{id(operation)}_task_id'] = task_id
                except Exception as e:
                    self.logger.warning(f"Failed to resolve task identifier for delete: {e}")
        
        # Fallback to common task_id
        if not task_id:
            task_id = context.get('task_id')
        
        if not task_id:
            raise ValueError("Task ID not found for delete operation")
        
        from src.models.command import ParsedCommand
        command = ParsedCommand(
            action=ActionType.DELETE_TASK,
            task_id=task_id,
        )
        
        return await self.task_manager.delete_task(command)
    
    async def _execute_move_task(
        self,
        operation: Operation,
        context: Dict[str, Any],
    ) -> str:
        """Execute move_task operation"""
        # Prefer operation-specific task_id for multiple operations support
        task_id = None
        if operation.task_identifier:
            task_id = context.get(f'operation_{id(operation)}_task_id')
            if not task_id:
                # Try to resolve it now
                try:
                    task_id = await self._resolve_task_identifier(operation.task_identifier)
                    context[f'operation_{id(operation)}_task_id'] = task_id
                except Exception as e:
                    self.logger.warning(f"Failed to resolve task identifier for move: {e}")
        
        # Fallback to common task_id
        if not task_id:
            task_id = context.get('task_id')
        
        if not task_id:
            raise ValueError("Task ID not found for move operation")
        
        target_project_id = operation.params.get("targetProjectId")
        if not target_project_id:
            raise ValueError("targetProjectId not specified for move operation")
        
        from src.models.command import ParsedCommand
        command = ParsedCommand(
            action=ActionType.MOVE_TASK,
            task_id=task_id,
            target_project_id=target_project_id,
        )
        
        return await self.task_manager.move_task(command)
    
    async def _execute_bulk_move(
        self,
        operation: Operation,
        context: Dict[str, Any],
    ) -> str:
        """Execute bulk_move operation"""
        from datetime import datetime
        from src.models.command import ParsedCommand
        
        from_date = operation.params.get("fromDate")
        to_date = operation.params.get("toDate")
        
        if not from_date or not to_date:
            raise ValueError("fromDate and toDate required for bulk_move")
        
        count = await self.batch_processor.move_overdue_tasks(
            from_date=datetime.fromisoformat(from_date),
            to_date=datetime.fromisoformat(to_date),
        )
        
        return f"✓ Перенесено {count} просроченных задач"
    
    async def _execute_add_tags(
        self,
        operation: Operation,
        context: Dict[str, Any],
    ) -> str:
        """Execute add_tags operation"""
        # Prefer operation-specific task_id for multiple operations support
        task_id = None
        if operation.task_identifier:
            task_id = context.get(f'operation_{id(operation)}_task_id')
            if not task_id:
                # Try to resolve it now
                try:
                    task_id = await self._resolve_task_identifier(operation.task_identifier)
                    context[f'operation_{id(operation)}_task_id'] = task_id
                except Exception as e:
                    self.logger.warning(f"Failed to resolve task identifier for add_tags: {e}")
        
        # Fallback to common task_id
        if not task_id:
            task_id = context.get('task_id')
        
        if not task_id:
            raise ValueError("Task ID not found for add_tags operation")
        
        tags = operation.params.get("tags")
        if not tags:
            raise ValueError("Tags not specified")
        
        from src.models.command import ParsedCommand
        command = ParsedCommand(
            action=ActionType.ADD_TAGS,
            task_id=task_id,
            tags=tags,
        )
        
        return await self.tag_manager.add_tags(command)
    
    async def _execute_add_note(
        self,
        operation: Operation,
        context: Dict[str, Any],
    ) -> str:
        """Execute add_note operation"""
        # Prefer operation-specific task_id for multiple operations support
        task_id = None
        if operation.task_identifier:
            task_id = context.get(f'operation_{id(operation)}_task_id')
            if not task_id:
                # Try to resolve it now
                try:
                    task_id = await self._resolve_task_identifier(operation.task_identifier)
                    context[f'operation_{id(operation)}_task_id'] = task_id
                except Exception as e:
                    self.logger.warning(f"Failed to resolve task identifier for add_note: {e}")
        
        # Fallback to common task_id
        if not task_id:
            task_id = context.get('task_id')
        
        if not task_id:
            raise ValueError("Task ID not found for add_note operation")
        
        notes = operation.params.get("notes")
        if not notes:
            raise ValueError("Notes not specified")
        
        from src.models.command import ParsedCommand
        command = ParsedCommand(
            action=ActionType.ADD_NOTE,
            task_id=task_id,
            notes=notes,
        )
        
        return await self.note_manager.add_note(command)
    
    async def _execute_create_recurring_task(
        self,
        operation: Operation,
        context: Dict[str, Any],
    ) -> str:
        """Execute create_recurring_task operation"""
        from src.models.command import ParsedCommand, Recurrence
        
        recurrence = operation.params.get("recurrence")
        if recurrence:
            recurrence_obj = Recurrence(**recurrence)
        else:
            recurrence_obj = None
        
        command = ParsedCommand(
            action=ActionType.CREATE_RECURRING_TASK,
            title=operation.params.get("title"),
            project_id=operation.params.get("projectId"),
            due_date=operation.params.get("dueDate"),
            priority=operation.params.get("priority"),
            tags=operation.params.get("tags"),
            notes=operation.params.get("notes"),
            recurrence=recurrence_obj,
        )
        
        return await self.recurring_task_manager.create_recurring_task(command)
    
    async def _execute_set_reminder(
        self,
        operation: Operation,
        context: Dict[str, Any],
    ) -> str:
        """Execute set_reminder operation"""
        # Prefer operation-specific task_id for multiple operations support
        task_id = None
        if operation.task_identifier:
            task_id = context.get(f'operation_{id(operation)}_task_id')
            if not task_id:
                # Try to resolve it now
                try:
                    task_id = await self._resolve_task_identifier(operation.task_identifier)
                    context[f'operation_{id(operation)}_task_id'] = task_id
                except Exception as e:
                    self.logger.warning(f"Failed to resolve task identifier for set_reminder: {e}")
        
        # Fallback to common task_id
        if not task_id:
            task_id = context.get('task_id')
        
        if not task_id:
            raise ValueError("Task ID not found for set_reminder operation")
        
        reminder = operation.params.get("reminder")
        if not reminder:
            raise ValueError("Reminder time not specified")
        
        from src.models.command import ParsedCommand
        command = ParsedCommand(
            action=ActionType.SET_REMINDER,
            task_id=task_id,
            reminder=reminder,
        )
        
        return await self.reminder_manager.set_reminder(command)
    
    async def _execute_get_analytics(
        self,
        operation: Operation,
        context: Dict[str, Any],
    ) -> str:
        """Execute get_analytics operation"""
        period = operation.params.get("period", "week")
        return await self.analytics_service.get_work_time_analytics(period)
    
    async def _execute_optimize_schedule(
        self,
        operation: Operation,
        context: Dict[str, Any],
    ) -> str:
        """Execute optimize_schedule operation"""
        return await self.analytics_service.optimize_schedule()
    
    async def _route_legacy(self, command: ParsedCommand) -> str:
        """
        Route legacy single-action command (backward compatibility)
        
        Args:
            command: Legacy ParsedCommand
            
        Returns:
            Response message
        
        Note: This should not be called directly - legacy commands are handled
        by main.py's execute_command method.
        """
        raise NotImplementedError("Legacy routing should be handled by main.py's execute_command method")
    
    def _combine_results(self, results: List[str]) -> str:
        """
        Combine multiple result messages
        
        Args:
            results: List of result messages
            
        Returns:
            Combined message
        """
        if len(results) == 1:
            return results[0]
        
        # Format combined message with cleaner output
        # Remove duplicate prefixes and make it more readable
        clean_results = []
        for r in results:
            # Remove common prefixes like "✓ " if present
            clean = r.replace("✓ ", "").strip()
            clean_results.append(clean)
        
        return f"✓ Выполнено {len(results)} операций:\n" + "\n".join(f"  • {r}" for r in clean_results)

