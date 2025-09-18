"""
Утилиты отображения для Rich интерфейса
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.tree import Tree
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich import box
from rich.rule import Rule
from rich.align import Align


class DisplayUtils:
    """Утилиты для красивого отображения в терминале"""
    
    def __init__(self, console: Console):
        self.console = console
    
    def print_header(self):
        """Отображение заголовка приложения"""
        header_text = Text("🧠 Smart Gemini FileSystem Agent", style="bold white")
        subtitle_text = Text("Intelligent file operations with intent analysis", style="dim white")
        
        header_panel = Panel(
            Align.center(f"{header_text}\n{subtitle_text}"),
            style="bold blue",
            box=box.DOUBLE
        )
        
        self.console.print(header_panel)
        self.console.print()
    
    def print_status_bar(self, agent=None):
        """Статус-бар с информацией о системе"""
        if not agent:
            status_text = "🔧 Agent not initialized"
        else:
            status = agent.get_status()
            tools_count = status.get('total_tools', 0)
            memory_status = "🧠 Memory" if status.get('use_memory', False) else "🚫 No Memory"
            
            status_text = (
                          f"🔧 Smart Gemini Agent "
                          f"📁 {os.path.basename(status.get('working_directory', '/'))} "
                          f"{memory_status} "
                          f"🔧 {tools_count} tools "
                          f"💬 Thread: main")
        
        status_panel = Panel(
            status_text,
            title="System Status",
            style="dim blue",
            box=box.ROUNDED
        )
        
        self.console.print(status_panel)

    def display_tool_call(self, tool_name: str, tool_args: dict):
        """Отображение вызова инструмента"""
        self.console.print(Panel(
            f"[bold cyan]{tool_name}[/bold cyan]\n[dim]{tool_args}[/dim]",
            title="[yellow]🛠️ Calling Tool[/yellow]",
            border_style="yellow",
            expand=False
        ))

    def display_tool_result(self, tool_name: str, content: str):
        """Отображение результата работы инструмента"""
        # Обрезаем длинный вывод
        if len(content) > 300:
            content = content[:300] + "..."
        self.console.print(Panel(
            f"[dim]{content}[/dim]",
            title=f"[green]✅ Tool '{tool_name}' Result[/green]",
            border_style="green",
            expand=False
        ))

    def display_agent_thought(self, thought: str):
        """Отображение мыслей агента"""
        self.console.print(Panel(
            f"[dim italic]{thought}[/dim italic]",
            title="[bold dim]🤔 Thinking...[/bold dim]",
            border_style="dim",
            expand=False
        ))

    def display_file_tree(self, start_path: str, max_depth: int = 3, show_hidden: bool = False):
        """Отображение дерева файлов"""
        path = Path(start_path)
        if not path.exists():
            self.display_error(f"Path does not exist: {start_path}")
            return

        def add_tree_items(tree_node, current_path, current_depth: int = 0):
            if current_depth >= max_depth:
                return
            
            try:
                items = []
                path_obj = Path(current_path)
                
                for item in path_obj.iterdir():
                    if not show_hidden and item.name.startswith('.'):
                        continue
                    items.append(item)
                
                items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
                
                for item in items:
                    if item.is_dir():
                        branch = tree_node.add(f"📁 {item.name}/", style="bold blue")
                        add_tree_items(branch, item, current_depth + 1)
                    else:
                        try:
                            size = item.stat().st_size
                            size_str = self._format_file_size(size)
                            tree_node.add(f"{self._get_file_emoji(item.name)} {item.name} [dim]({size_str})[/dim]", style=self._get_file_color(item.name))
                        except (OSError, PermissionError):
                            tree_node.add(f"{self._get_file_emoji(item.name)} {item.name} [dim](access denied)[/dim]", style="red")
                            
            except PermissionError:
                tree_node.add("❌ Access denied", style="red")
        
        tree = Tree(f"📂 {Path(path).name or path}", style="bold green")
        add_tree_items(tree, path, 0)
        
        panel = Panel(
            tree,
            title=f"[bold]File Tree: {path}[/bold]",
            border_style="green"
        )
        self.console.print(panel)
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Форматирование размера файла"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    def _get_file_emoji(self, filename: str) -> str:
        """Получение эмодзи для файла по расширению"""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        emoji_map = {
            'py': '🐍', 'js': '📜', 'ts': '📘', 'json': '📋',
            'md': '📝', 'txt': '📄', 'pdf': '📕', 'doc': '📘', 'docx': '📘',
            'xls': '📊', 'xlsx': '📊', 'csv': '📊',
            'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'svg': '🖼️',
            'mp4': '🎬', 'avi': '🎬', 'mov': '🎬',
            'mp3': '🎵', 'wav': '🎵', 'flac': '🎵',
            'zip': '📦', 'rar': '📦', '7z': '📦', 'tar': '📦',
            'exe': '⚙️', 'msi': '⚙️', 'deb': '⚙️', 'rpm': '⚙️',
            'html': '🌐', 'css': '🎨', 'xml': '📰',
            'sql': '🗃️', 'db': '🗃️', 'sqlite': '🗃️',
            'log': '📜', 'cfg': '⚙️', 'conf': '⚙️', 'ini': '⚙️'
        }
        
        return emoji_map.get(extension, '📄')
    
    def _get_file_color(self, filename: str) -> str:
        """Получение цвета для файла по расширению"""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        color_map = {
            'py': 'green', 'js': 'yellow', 'ts': 'blue', 'json': 'cyan',
            'md': 'magenta', 'txt': 'white',
            'jpg': 'bright_magenta', 'jpeg': 'bright_magenta', 'png': 'bright_magenta',
            'mp4': 'red', 'mp3': 'bright_green',
            'zip': 'bright_yellow', 'exe': 'bright_red',
            'html': 'bright_blue', 'css': 'bright_cyan',
            'log': 'dim white'
        }
        
        return color_map.get(extension, 'white')
    
    def display_help(self):
        """Отображение справки по командам"""
        commands = {
            "Системные команды": {
                "/help": "Показать эту справку",
                "/status": "Статус агента и инструментов",
                "/history [N]": "История команд (последние N)",
                "/clear": "Очистить экран",
                "/tree [path]": "Показать файловую структуру",
                "/tools": "Показать доступные инструменты",
                "/export": "Экспорт истории в файл",
                "/quit": "Выход из программы"
            },
            "Файловые операции": {
                "создай файл test.txt": "Создать новый файл",
                "прочитай config.py": "Показать содержимое файла",
                "удали старый.txt": "Удалить файл (безопасно)",
                "покажи файлы": "Список файлов в директории",
                "найди *.py": "Поиск файлов по маске"
            },
            "Веб-операции": {
                "найди в интернете Python": "Поиск в интернете",
                "скачай https://...": "Загрузить файл по URL"
            }
        }
        
        help_panels = []
        for category, cmds in commands.items():
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("Command", style="cyan", no_wrap=True)
            table.add_column("Description", style="white")
            
            for cmd, desc in cmds.items():
                table.add_row(cmd, desc)
            
            panel = Panel(table, title=f"[bold]{category}[/bold]", border_style="blue")
            help_panels.append(panel)
        
        self.console.print(Columns(help_panels, equal=True, expand=True))
    
    def display_history(self, history: List, limit: int = 10):
        """Отображение истории команд"""
        if not history:
            self.console.print("[yellow]История пуста[/yellow]")
            return
        
        table = Table(title="История команд", box=box.ROUNDED)
        table.add_column("#", style="dim", width=4)
        table.add_column("Время", style="cyan", width=20)
        table.add_column("Тип", style="magenta", width=10)
        table.add_column("Команда/Ответ", style="white")
        
        recent_history = history[-limit:] if len(history) > limit else history
        
        for i, entry in enumerate(recent_history, 1):
            timestamp = entry.get('timestamp', 'N/A')
            entry_type = entry.get('type', 'unknown')
            content = entry.get('content', '')
            
            if len(content) > 80:
                content = content[:77] + "..."
            
            type_style = {
                'user': 'green',
                'agent': 'blue', 
                'error': 'red'
            }.get(entry_type, 'white')
            
            table.add_row(str(i), timestamp, f"[{type_style}]{entry_type}[/{type_style}]", content)
        
        self.console.print(table)
    
    def display_agent_response(self, response: str, response_time: Optional[float] = None):
        """Красивое отображение ответа агента"""
        if response.startswith("Содержимое текущей рабочей директории:"):
            content = Text(response)
            panel = Panel(
                content,
                title="[bold green]🤖 Gemini Response[/bold green]",
                border_style="green"
            )
        elif response.startswith('```') and response.endswith('```'):
            lines = response.strip('`').split('\n')
            language = lines[0] if lines[0] else 'text'
            code = '\n'.join(lines[1:])
            
            syntax = Syntax(code, language, theme="monokai", line_numbers=True)
            panel = Panel(
                syntax,
                title="[bold green]🤖 Gemini Response (Code)[/bold green]",
                border_style="green"
            )
        else:
            try:
                content = Markdown(response)
            except:
                content = Text(response)
            
            panel = Panel(
                content,
                title="[bold green]🤖 Gemini Response[/bold green]",
                border_style="green"
            )
        
        self.console.print(panel)
        
        if response_time:
            self.console.print(f"[dim]⏱️ Response time: {response_time:.2f}s[/dim]")
    
    def display_error(self, error_message: str):
        """Отображение ошибки"""
        panel = Panel(
            f"❌ {error_message}",
            title="[bold red]Error[/bold red]",
            border_style="red"
        )
        self.console.print(panel)
    
    def display_success(self, message: str):
        """Отображение успешного выполнения"""
        panel = Panel(
            f"✅ {message}",
            title="[bold green]Success[/bold green]",
            border_style="green"
        )
        self.console.print(panel)
    
    def display_status_info(self, status: Dict[str, Any]):
        """Подробное отображение статуса системы"""
        main_table = Table(title="[bold]🤖 Smart Agent Status[/bold]", box=box.ROUNDED)
        main_table.add_column("Property", style="cyan")
        main_table.add_column("Value", style="green")
        
        simple_status = {k: v for k, v in status.items() 
                        if not isinstance(v, (dict, list)) or k == 'intelligence_features'}
        
        for key, value in simple_status.items():
            if key == 'intelligence_features':
                value = ', '.join(value)
            table_key = key.replace('_', ' ').title()
            main_table.add_row(table_key, str(value))
        
        self.console.print(main_table)
        
        if 'tools_by_category' in status and status['tools_by_category']:
            tools_table = Table(title="[bold]🔧 Tools by Category[/bold]", box=box.SIMPLE)
            tools_table.add_column("Category", style="magenta")
            tools_table.add_column("Count", style="yellow", justify="right")
            
            category_icons = {
                'read_file': '📖',
                'write_file': '✏️',
                'list_directory': '📁',
                'create_directory': '📂',
                'delete_file': '🗑️',
                'move_file': '📦',
                'search': '🔍',
                'web_search': '🌐',
                'fetch_url': '⬇️',
                'other': '🔧'
            }
            
            for category, count in status['tools_by_category'].items():
                icon = category_icons.get(category, '•')
                category_name = category.replace('_', ' ').title()
                tools_table.add_row(f"{icon} {category_name}", str(count))
            
            self.console.print(tools_table)
        
        if status.get('context_memory_items', 0) > 0:
            memory_panel = Panel(
                f"🧠 Context Memory: {status['context_memory_items']} items\n"
                f"🎯 Last Intent: {status.get('last_intent', 'None')}",
                title="[bold]Memory Status[/bold]",
                border_style="blue"
            )
            self.console.print(memory_panel)
    
    def clear_screen(self):
        """Очистка экрана"""
        self.console.clear()
    
    def print_rule(self, title: str = None):
        """Печать разделительной линии"""
        self.console.print(Rule(title, style="dim"))
