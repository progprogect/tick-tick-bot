"""
Analytics service
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from src.api.ticktick_client import TickTickClient
from src.services.gpt_service import GPTService
from src.utils.logger import logger
from src.utils.formatters import format_analytics


class AnalyticsService:
    """Service for analytics and reporting"""
    
    def __init__(self, ticktick_client: TickTickClient, gpt_service: GPTService):
        """
        Initialize analytics service
        
        Args:
            ticktick_client: TickTick API client
            gpt_service: GPT service for analysis
        """
        self.client = ticktick_client
        self.gpt_service = gpt_service
        self.logger = logger
    
    async def get_work_time_analytics(
        self,
        period: str = "week",
    ) -> str:
        """
        Get work time analytics for period
        
        Args:
            period: Period for analytics (week, month, year)
            
        Returns:
            Formatted analytics message
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            
            if period == "week":
                start_date = end_date - timedelta(weeks=1)
                period_text = "прошлую неделю"
            elif period == "month":
                start_date = end_date - timedelta(days=30)
                period_text = "прошлый месяц"
            elif period == "year":
                start_date = end_date - timedelta(days=365)
                period_text = "прошлый год"
            else:
                start_date = end_date - timedelta(weeks=1)
                period_text = "период"
            
            # Get tasks for period
            # Format dates with timezone for API
            start_date_str = start_date.isoformat() + '+00:00'
            end_date_str = end_date.isoformat() + '+00:00'
            
            # Get tasks for period
            # Note: TickTick API /project/{projectId}/data does not return completed tasks (status=2)
            # We can only get incomplete tasks (status=0) through this endpoint
            # For analytics, we'll use tasks with dueDate in the period, regardless of completion status
            # This is a limitation of the TickTick API - completed tasks are not accessible via /data endpoint
            tasks = await self.client.get_tasks(
                start_date=start_date_str,
                end_date=end_date_str,
                # Don't filter by status - get all tasks from /data (which only returns incomplete)
                # Completed tasks would need to be tracked separately via cache or direct GET
            )
            
            if not tasks:
                return f"За {period_text} задач не найдено"
            
            # Calculate work time
            work_time = 0
            personal_time = 0
            
            for task in tasks:
                # Check if task is work-related (by project or tags)
                project_id = task.get("projectId", "").lower()
                tags = [tag.lower() for tag in task.get("tags", [])]
                
                # Estimate time based on task completion or tags
                # This is a simplified calculation - in real scenario,
                # you might need to track actual time spent
                estimated_time = 0.5  # Default 30 minutes per task
                
                if "работа" in project_id or "work" in project_id or any(
                    "работа" in tag or "work" in tag for tag in tags
                ):
                    work_time += estimated_time
                elif "личное" in project_id or "personal" in project_id or any(
                    "личное" in tag or "personal" in tag for tag in tags
                ):
                    personal_time += estimated_time
                else:
                    # Default to work time
                    work_time += estimated_time
            
            total_time = work_time + personal_time
            
            analytics = {
                "period": period_text,
                "work_time": int(work_time),
                "personal_time": int(personal_time),
                "total_time": int(total_time),
            }
            
            return format_analytics(analytics)
            
        except Exception as e:
            self.logger.error(f"Error getting analytics: {e}", exc_info=True)
            raise
    
    async def optimize_schedule(
        self,
        period: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        """
        Analyze schedule and provide optimization recommendations
        
        Args:
            period: Period for analysis ("today", "week", "month")
            start_date: Start date in ISO format
            end_date: End date in ISO format
            
        Returns:
            Optimization recommendations
        """
        try:
            # Calculate date range if period is specified
            if period and not start_date:
                from datetime import datetime, timedelta
                now = datetime.now()
                
                if period == "today":
                    start_date = now.strftime("%Y-%m-%dT00:00:00+00:00")
                    end_date = now.strftime("%Y-%m-%dT23:59:59+00:00")
                elif period == "week":
                    start_date = now.strftime("%Y-%m-%dT00:00:00+00:00")
                    end_date = (now + timedelta(days=7)).strftime("%Y-%m-%dT23:59:59+00:00")
                elif period == "month":
                    start_date = now.strftime("%Y-%m-%dT00:00:00+00:00")
                    end_date = (now + timedelta(days=30)).strftime("%Y-%m-%dT23:59:59+00:00")
            
            # Get tasks with date filter
            tasks = await self.client.get_tasks(
                status=0,  # Incomplete only
                start_date=start_date,
                end_date=end_date,
            )
            
            if not tasks:
                period_text = period or "указанный период"
                return f"Нет активных задач для анализа на {period_text}"
            
            # Get projects
            projects = await self.client.get_projects()
            
            # Analyze with GPT
            period_text = period or "указанный период"
            prompt = f"""Проанализируй следующее расписание на {period_text} и предложи оптимизацию:
            
Задачи:
{self._format_tasks_for_analysis(tasks)}

Списки:
{self._format_projects_for_analysis(projects)}

Предложи:
1. Перераспределение задач по времени
2. Изменение приоритетов
3. Улучшение планирования

Верни рекомендации в текстовом формате."""
            
            recommendations = await self.gpt_service.openai_client.chat_completion([
                {"role": "system", "content": "Ты - эксперт по управлению временем и оптимизации расписания."},
                {"role": "user", "content": prompt},
            ])
            
            return f"📊 Анализ расписания на {period_text}:\n\n{recommendations}"
            
        except Exception as e:
            self.logger.error(f"Error optimizing schedule: {e}", exc_info=True)
            raise
    
    async def list_tasks(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> str:
        """
        List tasks for a given date range with intelligent formatting
        
        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format
            project_id: Optional project ID to filter by
            
        Returns:
            Formatted list of tasks with GPT analysis
        """
        try:
            # Step 1: Get tasks from API
            tasks = await self.client.get_tasks(
                project_id=project_id,
                status=0,  # Incomplete only
                start_date=start_date,
                end_date=end_date,
            )
            
            if not tasks:
                if start_date and end_date:
                    return "📋 На указанный период задач не найдено"
                else:
                    return "📋 Активных задач не найдено"
            
            # Step 2: Format date range for display
            date_range = ""
            if start_date and end_date:
                try:
                    from datetime import datetime
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    if start_dt.date() == end_dt.date():
                        date_range = f" на {start_dt.strftime('%d.%m.%Y')}"
                    else:
                        date_range = f" с {start_dt.strftime('%d.%m.%Y')} по {end_dt.strftime('%d.%m.%Y')}"
                except:
                    pass
            
            # Step 3: Format tasks data for GPT
            tasks_data = self._format_tasks_for_analysis(tasks)
            
            # Step 4: Use GPT to create intelligent summary
            try:
                prompt = f"""Пользователь спрашивает о своих задачах{date_range}.

Вот список задач:
{tasks_data}

Создай краткий, дружелюбный ответ на русском языке, который:
1. Кратко резюмирует, что у пользователя запланировано
2. Выделяет самые важные/срочные задачи (если есть)
3. Дает общее впечатление о загруженности (много/мало задач)
4. Будь кратким (2-3 предложения) и дружелюбным

Ответ должен начинаться с "📋" и быть естественным, как будто ты личный ассистент."""
                
                gpt_response = await self.gpt_service.openai_client.chat_completion([
                    {"role": "system", "content": "Ты - дружелюбный личный ассистент, который помогает пользователю управлять задачами."},
                    {"role": "user", "content": prompt},
                ])
                
                # Add task list below GPT summary
                formatted_list = []
                for task in tasks[:10]:  # Limit to 10 for display
                    title = task.get('title', 'Без названия')
                    due_date = task.get('dueDate', '')
                    priority = task.get('priority', 0)
                    tags = task.get('tags', [])
                    
                    # Format date
                    if due_date:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                            due_date_str = dt.strftime('%d.%m %H:%M')
                        except:
                            due_date_str = due_date
                    else:
                        due_date_str = None
                    
                    # Format task line
                    task_line = f"• {title}"
                    if due_date_str:
                        task_line += f" (до {due_date_str})"
                    if priority > 0:
                        priority_names = {1: "низкий", 2: "средний", 3: "высокий"}
                        priority_str = priority_names.get(priority, "")
                        if priority_str:
                            task_line += f" [{priority_str}]"
                    if tags:
                        task_line += f" #{', '.join(tags[:2])}"  # Limit tags
                    
                    formatted_list.append(task_line)
                
                result = gpt_response.strip()
                if formatted_list:
                    result += f"\n\n📝 Список задач:\n" + "\n".join(formatted_list)
                if len(tasks) > 10:
                    result += f"\n\n... и еще {len(tasks) - 10} задач"
                result += f"\n\nВсего: {len(tasks)} задач"
                
                return result
                
            except Exception as gpt_error:
                # Fallback to simple formatting if GPT fails
                self.logger.warning(f"GPT formatting failed, using simple format: {gpt_error}")
                
                formatted_tasks = []
                for task in tasks:
                    title = task.get('title', 'Без названия')
                    due_date = task.get('dueDate', '')
                    priority = task.get('priority', 0)
                    tags = task.get('tags', [])
                    
                    if due_date:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                            due_date_str = dt.strftime('%d.%m.%Y %H:%M')
                        except:
                            due_date_str = due_date
                    else:
                        due_date_str = "Без даты"
                    
                    priority_names = {0: "обычный", 1: "низкий", 2: "средний", 3: "высокий"}
                    priority_str = priority_names.get(priority, f"приоритет {priority}")
                    
                    task_line = f"• {title}"
                    if due_date_str != "Без даты":
                        task_line += f" (до {due_date_str})"
                    if priority > 0:
                        task_line += f" [{priority_str}]"
                    if tags:
                        task_line += f" #{', '.join(tags)}"
                    
                    formatted_tasks.append(task_line)
                
                result = f"📋 Ваши задачи{date_range}:\n\n"
                result += "\n".join(formatted_tasks)
                result += f"\n\nВсего: {len(tasks)} задач"
                
                return result
            
        except Exception as e:
            self.logger.error(f"Error listing tasks: {e}", exc_info=True)
            raise
    
    def _format_tasks_for_analysis(self, tasks: list) -> str:
        """Format tasks for GPT analysis"""
        formatted = []
        for task in tasks[:20]:  # Limit to 20 tasks
            formatted.append(
                f"- {task.get('title', '')} "
                f"(Due: {task.get('dueDate', 'Не указана')}, "
                f"Priority: {task.get('priority', 0)})"
            )
        return "\n".join(formatted)
    
    def _format_projects_for_analysis(self, projects: list) -> str:
        """Format projects for GPT analysis"""
        formatted = []
        for project in projects[:10]:  # Limit to 10 projects
            formatted.append(f"- {project.get('name', '')}")
        return "\n".join(formatted)


