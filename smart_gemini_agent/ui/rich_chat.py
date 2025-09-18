"""
Rich терминальный интерфейс для Smart Gemini Agent
"""

import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.status import Status
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from .display_utils import DisplayUtils


class RichInteractiveChat:
    """Богатый терминальный интерфейс для AI-агента"""
    
    def __init__(self, agent):
        self.console = Console()
        self.agent = agent
        self.history = []
        self.current_thread = "main"
        self.show_timestamps = True
        self.theme = "dark"
        
        # Инициализируем утилиты отображения
        self.display = DisplayUtils(self.console)
        
        # Стили
        self.styles = {
            "user": "bold blue",
            "agent": "green",
            "system": "yellow",
            "error": "bold red",
            "success": "bold green",
            "info": "cyan",
            "warning": "orange3",
            "path": "bold magenta",
            "command": "bold white on blue"
        }
    
    def clear_screen(self):
        """Очистка экрана"""
        self.console.clear()
    
    def get_user_input(self) -> Optional[str]:
        """Получение ввода от пользователя"""
        try:
            user_input = Prompt.ask(
                "[bold blue]💬 You[/bold blue]",
                console=self.console
            ).strip()
            
            return user_input if user_input else None
            
        except (KeyboardInterrupt, EOFError):
            return None
    
    def add_to_history(self, content: str, entry_type: str):
        """Добавление записи в историю"""
        timestamp = datetime.now().strftime("%H:%M:%S") if self.show_timestamps else ""
        
        self.history.append({
            'timestamp': timestamp,
            'type': entry_type,
            'content': content
        })
        
        # Ограничиваем размер истории
        if len(self.history) > 1000:
            self.history = self.history[-500:]
    
    def process_system_command(self, command: str) -> bool:
        """
        Обработка системных команд
        
        Returns:
            True если команда обработана, False если нужно продолжить
        """
        command = command.lower().strip()
        
        if command == "/quit" or command == "/exit":
            return False
        
        elif command == "/help":
            self.display.display_help()
        
        elif command == "/clear":
            self.clear_screen()
            self.display.print_header()
            self.display.print_status_bar(self.agent)
        
        elif command == "/status":
            if self.agent:
                status = self.agent.get_status()
                self.display.display_status_info(status)
            else:
                self.display.display_error("Agent not initialized")
        
        elif command.startswith("/history"):
            parts = command.split()
            limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
            self.display.display_history(self.history, limit)
        
        elif command.startswith("/tree"):
            parts = command.split(maxsplit=1)
            path = parts[1] if len(parts) > 1 else "."
            try:
                self.display.display_file_tree(path)
            except Exception as e:
                self.display.display_error(f"Cannot display tree for '{path}': {e}")
        
        elif command == "/tools":
            self.display_tools_info()
        
        elif command == "/export":
            self.export_history()
        
        elif command == "/reload":
            if self.agent:
                try:
                    new_prompt = self.agent.reload_prompt()
                    self.display.display_success("Prompt reloaded successfully")
                except Exception as e:
                    self.display.display_error(f"Failed to reload prompt: {e}")
            else:
                self.display.display_error("Agent not initialized")
        
        elif command == "/memory":
            if self.agent:
                self.agent.clear_context_memory()
                self.display.display_success("Context memory cleared")
            else:
                self.display.display_error("Agent not initialized")
        
        else:
            self.display.display_error(f"Unknown command: {command}")
            self.display.display_help()
        
        return True
    
    def display_tools_info(self):
        """Отображение доступных инструментов с категоризацией"""
        if not self.agent or not hasattr(self.agent, 'tools_map'):
            self.display.display_error("Agent not initialized or tools not loaded")
            return
        
        # Создаем таблицу инструментов по категориям
        for category, tools in self.agent.tools_map.items():
            if not tools:
                continue
            
            table = Table(title=f"[bold]{category.replace('_', ' ').title()}[/bold]", box=box.ROUNDED)
            table.add_column("Tool", style="cyan", no_wrap=True)
            table.add_column("Description", style="white")
            
            for tool in tools:
                description = getattr(tool, 'description', 'No description')
                if len(description) > 80:
                    description = description[:77] + "..."
                table.add_row(tool.name, description)
            
            self.console.print(table)
            self.console.print()
        
        # Показываем примеры использования
        examples_table = Table(title="[bold]💡 Smart Examples[/bold]", box=box.SIMPLE)
        examples_table.add_column("Command", style="green")
        examples_table.add_column("Description", style="white")
        
        examples = [
            ("создай файл readme.md с описанием проекта", "Create file with content"),
            ("прочитай config.json", "Read and format file content"),
            ("удали старый файл backup.txt", "Safe file deletion"),
            ("покажи файлы", "List directory contents"),
            ("найди файлы *.py", "Search for Python files"),
            ("найди в интернете информацию о Python", "Web search"),
        ]
        
        for cmd, desc in examples:
            examples_table.add_row(cmd, desc)
        
        self.console.print(examples_table)
    
    def export_history(self):
        """Экспорт истории в файл"""
        if not self.history:
            self.display.display_error("История пуста")
            return
        
        filename = f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("# Gemini AI Agent Chat History\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for entry in self.history:
                    timestamp = entry.get('timestamp', '')
                    entry_type = entry.get('type', 'unknown')
                    content = entry.get('content', '')
                    
                    f.write(f"## {entry_type.title()} [{timestamp}]\n\n")
                    f.write(f"{content}\n\n")
                    f.write("---\n\n")
            
            self.display.display_success(f"История экспортирована в {filename}")
            
        except Exception as e:
            self.display.display_error(f"Ошибка экспорта: {e}")
    
    def _display_step(self, chunk: Dict):
        """Отображение одного шага из потока LangGraph"""
        final_response = None
        if "agent" in chunk:
            agent_step = chunk["agent"]
            if isinstance(agent_step, dict) and agent_step.get("messages"):
                messages = agent_step["messages"]
                for msg in messages:
                    # Проверяем, является ли сообщение вызовом инструмента
                    if msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            self.display.display_tool_call(tool_call['name'], tool_call['args'])
                    # Если это не вызов инструмента, а есть контент, это мысль или финальный ответ
                    elif msg.content:
                        # Преобразуем контент в строку для проверки
                        content_str = ""
                        if isinstance(msg.content, list):
                            content_str = "\n".join(map(str, msg.content))
                        else:
                            content_str = str(msg.content)

                        # Проверяем, является ли это мыслью агента
                        if "Thought:" in content_str or "Plan:" in content_str:
                            self.display.display_agent_thought(content_str)
                        # В противном случае, это финальный ответ
                        else:
                            final_response = content_str

        # Отображаем результаты выполненных инструментов
        if "tools" in chunk:
            tool_steps = chunk["tools"]
            if isinstance(tool_steps, list):
                for tool_msg in tool_steps:
                    self.display.display_tool_result(tool_msg.name, tool_msg.content)

        # Логика для __end__ остается как запасной вариант
        if "__end__" in chunk:
            messages = chunk["__end__"].get("messages", [])
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, 'content') and last_message.content:
                    if isinstance(last_message.content, list):
                         final_response = "\n".join(map(str, last_message.content))
                    else:
                         final_response = str(last_message.content)

                # Улучшаем форматирование, если это возможно
                if final_response and self.agent and hasattr(self.agent, 'response_formatter'):
                    final_response = self.agent.response_formatter.improve_file_content_formatting(final_response)

        return final_response

    async def run(self):
        """Основной цикл чата"""
        self.clear_screen()
        self.display.print_header()
        self.display.print_status_bar(self.agent)
        
        self.console.print("[dim]Type /help for available commands, /quit to exit[/dim]")
        self.display.print_rule()
        
        while True:
            user_input = self.get_user_input()
            
            if user_input is None:
                break
            
            if not user_input:
                continue
            
            self.add_to_history(user_input, "user")
            
            if user_input.startswith('/'):
                if self.process_system_command(user_input):
                    continue
                else:
                    break
            
            if self.agent:
                try:
                    start_time = time.time()
                    final_response = None
                    has_called_tool_in_this_turn = False
                    had_error_in_this_turn = False
                    
                    self.console.print() # Пустая строка перед началом
                    self.display.print_rule(title="[bold yellow]Agent Activity[/bold yellow]")

                    async for chunk in self.agent.process_message(user_input, self.current_thread):
                        if "error" in chunk:
                            self.display.display_error(chunk["error"])
                            had_error_in_this_turn = True
                            final_response = None
                            break
                        
                        # Отслеживаем, был ли вызван инструмент в этом ходу
                        if "tools" in chunk and chunk["tools"]:
                            has_called_tool_in_this_turn = True

                        response_part = self._display_step(chunk)
                        if response_part:
                            final_response = response_part

                    self.display.print_rule()
                    self.console.print() # Пустая строка после

                    if final_response:
                        response_time = time.time() - start_time
                        self.add_to_history(final_response, "agent")
                        self.display.display_agent_response(final_response, response_time)
                    elif has_called_tool_in_this_turn and not had_error_in_this_turn:
                        final_response = "✅ Задача успешно выполнена."
                        response_time = time.time() - start_time
                        self.add_to_history(final_response, "agent")
                        self.display.display_agent_response(final_response, response_time)
                    elif not had_error_in_this_turn:
                        self.console.print("⚠️ [yellow]Agent finished without a final response.[/yellow]")

                except Exception as e:
                    error_msg = f"Error processing message: {str(e)}"
                    self.add_to_history(error_msg, "error")
                    self.display.display_error(error_msg)
            else:
                self.display.display_error("Agent not initialized")
            
            self.console.print()
        
        self.console.print("[dim]Goodbye! 👋[/dim]")
