"""
Основной класс Smart Gemini Agent
"""

import os
import re

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core.exceptions import ResourceExhausted
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

from ..config.agent_config import AgentConfig
from ..tools.delete_tools import SafeDeleteFileTool, SafeDeleteDirectoryTool
from ..tools.tool_analyzer import ToolAnalyzer
from ..utils.decorators import retry_on_failure, retry_on_failure_async_gen
from .intent_analyzer import IntentAnalyzer
from .prompt_manager import PromptManager
from .response_formatter import ResponseFormatter

logger = logging.getLogger(__name__)


class FileSystemAgent:
    """
    Умный AI-агент для работы с файловой системой на базе Google Gemini
    с поддержкой Model Context Protocol (MCP)
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent = None
        self.checkpointer = None
        self.mcp_client = None
        self.tools = []
        self._initialized = False
        
        # Инициализируем компоненты
        self.tool_analyzer = ToolAnalyzer()
        self.intent_analyzer = IntentAnalyzer(debug_mode=config.debug_intent_analysis)
        self.prompt_manager = PromptManager(config)
        self.response_formatter = ResponseFormatter(debug_mode=config.debug_intent_analysis)
        
        logger.info("Создан умный агент с Gemini")
        logger.info(f"Рабочая директория: {config.filesystem_path}")
    
    @property
    def is_ready(self) -> bool:
        """Проверяет готовность агента"""
        return self._initialized and self.agent is not None
    
    async def initialize(self) -> bool:
        """Инициализация агента"""
        if self._initialized:
            logger.warning("Агент уже инициализирован")
            return True
        
        logger.info("Инициализация агента...")
        
        try:
            self.config.validate()
            await self._init_mcp_client()
            
            # Создание Gemini модели
            api_key = os.getenv("GOOGLE_API_KEY")
            model = ChatGoogleGenerativeAI(
                model=self.config.model_name,
                google_api_key=api_key,
                temperature=self.config.temperature
            )
            
            if self.config.use_memory:
                self.checkpointer = InMemorySaver()
                logger.info("Память агента включена")
            
            # Обновляем анализатор инструментов в менеджере промптов
            self.prompt_manager.update_tool_analyzer(self.tool_analyzer)
            
            self.agent = create_react_agent(
                model=model,
                tools=self.tools,
                checkpointer=self.checkpointer,
                prompt=self.prompt_manager.get_system_prompt()
            )
            
            self._initialized = True
            logger.info("✅ Агент успешно инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            return False
    
    @retry_on_failure()
    async def _init_mcp_client(self):
        """Инициализация MCP клиента"""
        logger.info("Инициализация MCP клиента...")
        
        # Временно подавить предупреждения во время инициализации
        old_level = logging.getLogger().level
        logging.getLogger().setLevel(logging.ERROR)
        
        try:
            self.mcp_client = MultiServerMCPClient(self.config.get_mcp_config())
            self.tools = await self.mcp_client.get_tools()
        finally:
            # Восстановить уровень логирования
            logging.getLogger().setLevel(old_level)
        
        if not self.tools:
            raise Exception("Нет доступных MCP инструментов")
        
        # Добавляем локальные инструменты для удаления
        self._add_local_tools()
        
        # Анализируем и категоризируем инструменты
        self.tools_map = self.tool_analyzer.analyze_tools(self.tools)
        
        logger.info(f"Загружено {len(self.tools)} инструментов")
        for tool in self.tools:
            logger.info(f"  • {tool.name}")
    
    def _add_local_tools(self):
        """Добавление локальных инструментов"""
        # Создаем локальные инструменты для удаления
        delete_file_tool = SafeDeleteFileTool(self.config.filesystem_path)
        delete_dir_tool = SafeDeleteDirectoryTool(self.config.filesystem_path)
        
        # Добавляем к списку инструментов
        self.tools.extend([delete_file_tool, delete_dir_tool])
        
        logger.info("Добавлены локальные инструменты:")
        logger.info(f"  • {delete_file_tool.name}: {delete_file_tool.description}")
        logger.info(f"  • {delete_dir_tool.name}: {delete_dir_tool.description}")
    
    @retry_on_failure_async_gen()
    async def process_message(self, user_input: str, thread_id: str = "default") -> AsyncGenerator[Dict, None]:
        """Умная обработка сообщения пользователя с анализом намерений и стримингом шагов"""
        if not self.is_ready:
            yield {"error": "Агент не готов. Попробуйте переинициализировать."}
            return
        
        try:
            # Анализируем намерения пользователя
            intent, params = self.intent_analyzer.analyze_intent(user_input)
            logger.info(f"Определено намерение: {intent}, параметры: {params}")

            # УЛУЧШЕНИЕ: Проверка параметров на адекватность (гибкая версия)
            file_intents = ['read_file', 'write_file', 'delete_file', 'refactor_file', 'move_file']
            if intent in file_intents:
                target = params.get('target')
                # Блокируем только заведомо неверные имена, но пропускаем None,
                # чтобы дать агенту шанс догадаться по контексту.
                invalid_keywords = ['исправь', 'поправь', 'улучши', 'создай', 'удали', 'прочитай', 'покажи']
                if target and target in invalid_keywords:
                    logger.warning(f"Недопустимое имя файла для намерения '{intent}': {target}")
                    yield {"error": f"Я не смог определить корректное имя файла в вашем запросе. Пожалуйста, уточните, с каким файлом нужно работать."}
                    return
            
            # Создаем улучшенный контекст на основе анализа
            enhanced_input = self._create_enhanced_context(user_input, intent, params)
            
            config = {"configurable": {"thread_id": thread_id}}
            message_input = {"messages": [HumanMessage(content=enhanced_input)]}
            
            async for chunk in self.agent.astream(message_input, config):
                yield chunk
            
        except ResourceExhausted as e:
            error_text = str(e)
            retry_secs = None
            m = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", error_text)
            if m:
                retry_secs = int(m.group(1))
            
            wait_hint = f"Пожалуйста, подождите примерно {retry_secs} секунд и повторите попытку." if retry_secs else "Пожалуйста, подождите немного и повторите попытку."
            
            friendly_error = (
                f"😔 **Превышены лимиты API Gemini (ошибка 429)**\n\n"
                f"{wait_hint}\n\n"
                f"Подробнее о квотах: https://ai.google.dev/gemini-api/docs/rate-limits"
            )
            yield {"error": friendly_error}
            
        except Exception as e:
            error_text = str(e)
            final_error_msg = f"❌ Ошибка обработки: {error_text}"
            logger.error(final_error_msg)
            import traceback
            logger.error(f"Трассировка: {traceback.format_exc()}")
            yield {"error": final_error_msg}

    
    def _create_enhanced_context(self, user_input: str, intent: str, params: Dict[str, Any]) -> str:
        """Создание улучшенного контекста на основе анализа намерений"""
        base_context = f"Рабочая директория: '{self.config.filesystem_path}'"

        # Обработка специальных типов файлов
        instruction = self._handle_special_file_types(user_input, intent, params)
        if not instruction:
            instruction = self._get_intent_instruction(intent)

        enhanced_context = f"""
{base_context}

{instruction}

ЗАПРОС ПОЛЬЗОВАТЕЛЯ: {user_input}

ПАРАМЕТРЫ: {params if params else 'Не извлечены'}
"""
        
        return enhanced_context.strip()

    def _get_intent_instruction(self, intent: str) -> str:
        """Получение инструкции по намерению."""
        intent_instructions = {
            'create_file': f"ЗАДАЧА: Создать файл. Рекомендуемые инструменты: {[t.name for t in self.tools_map.get('write_file', [])]}",
            'create_directory': f"ЗАДАЧА: Создать папку. Рекомендуемые инструменты: {[t.name for t in self.tools_map.get('create_directory', [])]}",
            'read_file': f"ЗАДАЧА: Прочитать файл. Рекомендуемые инструменты: {[t.name for t in self.tools_map.get('read_file', [])]}",
            'list_directory': f"ЗАДАЧА: Показать содержимое папки. Рекомендуемые инструменты: {[t.name for t in self.tools_map.get('list_directory', [])]}",
            'delete_file': self._get_delete_instruction(),
            'search': f"ЗАДАЧА: Поиск. Рекомендуемые инструменты: {[t.name for t in self.tools_map.get('search', [])]}",
            'web_search': f"ЗАДАЧА: Веб-поиск. Рекомендуемые инструменты: {[t.name for t in self.tools_map.get('web_search', [])]}"
        }
        return intent_instructions.get(intent, "ЗАДАЧА: Общий запрос")

    def _handle_special_file_types(self, user_input: str, intent: str, params: Dict[str, Any]) -> Optional[str]:
        """Обработка специальных типов файлов, таких как Excel."""
        target_file = params.get('target', '')
        if not target_file:
            return None

        if target_file.endswith(('.xlsx', '.xls')):
            return self._handle_excel_files(user_input, intent, params)

        return None

    def _handle_excel_files(self, user_input: str, intent: str, params: Dict[str, Any]) -> Optional[str]:
        """Обработка Excel файлов."""
        excel_tools = [t for t in self.tools if 'excel' in t.name.lower()]
        if not excel_tools:
            return None

        target_file = params.get('target', '')
        if not os.path.isabs(target_file):
            absolute_path = os.path.join(self.config.filesystem_path, target_file)
            params['target'] = absolute_path
            logger.info(f"Преобразован относительный путь {target_file} в абсолютный {absolute_path}")

        wants_chart = bool(re.search(r"(диаграм|chart|график)", user_input, re.IGNORECASE))
        if intent == 'create_file' and wants_chart:
            return (
                f"СПЕЦИАЛЬНАЯ ЗАДАЧА: Создать Excel файл с диаграммой. "
                f"Используйте Excel-специфичные инструменты: {[t.name for t in excel_tools]}. "
                f"ВАЖНО: Создайте простую круговую диаграмму с базовыми данными. Путь к файлу: {params['target']}"
            )
        return None
    
    def _get_delete_instruction(self) -> str:
        """Получение инструкции для удаления с приоритетом безопасных инструментов"""
        delete_tools = self.tools_map.get('delete_file', [])
        safe_tools = [t for t in delete_tools if 'safe_delete' in t.name]
        
        if safe_tools:
            return f"ЗАДАЧА: Удаление файла/папки. ПРИОРИТЕТ: {[t.name for t in safe_tools]} (безопасные инструменты)"
        else:
            return f"ЗАДАЧА: Удаление файла/папки. Доступные инструменты: {[t.name for t in delete_tools]}"
    
    def get_status(self) -> Dict[str, Any]:
        """Информация о состоянии умного агента"""
        tools_by_category = {k: len(v) for k, v in self.tools_map.items() if v}
        context_memory = self.intent_analyzer.get_context_memory()
        
        return {
            'initialized': self._initialized,
            'ready': self.is_ready,
            'model_name': self.config.model_name,
            'temperature': self.config.temperature,
            'use_memory': self.config.use_memory,
            'working_directory': self.config.filesystem_path,
            'total_tools': len(self.tools),
            'tools_by_category': tools_by_category,
            'context_memory_items': len(context_memory),
            'last_intent': context_memory.get('last_intent'),
            'intelligence_features': [
                'Intent Analysis',
                'Context Memory', 
                'Smart Tool Selection',
                'File Formatting',
                'Universal MCP Support'
            ]
        }
    
    def reload_prompt(self) -> str:
        """Перезагрузка промпта из файла"""
        return self.prompt_manager.reload_prompt()
    
    def clear_context_memory(self):
        """Очистка контекстной памяти"""
        self.intent_analyzer.clear_context_memory()
        logger.info("Контекстная память очищена")
    
    def get_tools_by_category(self, category: str) -> List:
        """Получение инструментов по категории"""
        return self.tools_map.get(category, [])
    
    def get_available_categories(self) -> List[str]:
        """Получение списка доступных категорий инструментов"""
        return [cat for cat, tools in self.tools_map.items() if tools]