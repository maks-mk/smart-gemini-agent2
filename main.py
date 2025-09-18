#!/usr/bin/env python3
"""
Smart Gemini Agent - Модульная версия
Точка входа для запуска агента
"""

import asyncio
import os
import json
import logging
from dotenv import load_dotenv
from rich.console import Console

from smart_gemini_agent import AgentConfig, FileSystemAgent, RichInteractiveChat
from smart_gemini_agent.config.logging_config import setup_logging


async def main():
    """Главная функция с Rich интерфейсом"""
    load_dotenv()
    
    # Загрузка конфигурации из файла для настройки логирования
    log_level = logging.INFO
    log_file = "ai_agent.log"
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            logging_cfg = cfg.get("logging", {})
            level_str = str(logging_cfg.get("level", "INFO")).upper()
            log_level = getattr(logging, level_str, logging.INFO)
            log_file = logging_cfg.get("file", log_file)
            log_format = logging_cfg.get("format", log_format)
    except Exception:
        # В случае ошибки применяем значения по умолчанию
        pass

    # Настройка логирования согласно конфигу
    logger = setup_logging(level=log_level, log_file=log_file, format_string=log_format)
    
    try:
        # Создание конфигурации из файла или переменных окружения
        config = AgentConfig.from_file("config.json")
        
        # Переопределяем из переменных окружения если они заданы
        if os.getenv("FILESYSTEM_PATH"):
            config.filesystem_path = os.getenv("FILESYSTEM_PATH")
        if os.getenv("GEMINI_MODEL"):
            config.model_name = os.getenv("GEMINI_MODEL")
        if os.getenv("TEMPERATURE"):
            config.temperature = float(os.getenv("TEMPERATURE"))
        
        # Создание и инициализация агента
        agent = FileSystemAgent(config)
        
        # Создаем богатый интерфейс для показа прогресса инициализации
        console = Console()
        
        with console.status("[bold green]Initializing Gemini Agent...", spinner="dots"):
            if not await agent.initialize():
                console.print("❌ [bold red]Не удалось инициализировать агента[/bold red]")
                return
        
        console.print("✅ [bold green]Gemini Agent successfully initialized![/bold green]")
        
        # Запуск богатого чата
        chat = RichInteractiveChat(agent)
        await chat.run()
        
    except Exception as e:
        Console().print(f"❌ [bold red]Критическая ошибка: {e}[/bold red]")
    
    logger.info("🏁 Завершение работы")


if __name__ == "__main__":
    asyncio.run(main())