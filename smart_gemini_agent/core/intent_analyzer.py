"""
Анализатор намерений пользователя
"""

import re
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """Класс для анализа намерений пользователя"""
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.context_memory: Dict[str, Any] = {}
        
        # Паттерны для различных операций
        self.intent_patterns = {
            'refactor_file': [
                r'(исправь|поправь|отформатируй|улучши|fix|format|refactor)\s+.*(?:в\s+файле|in\s+file)\s+([\w\._-]+)'
            ],
            'create_file': [
                r'(?:создай|создать|сделай|новый)\s+(?:excel\s+)?файл\s+([^\s]+)',
                r'(?:создай|создать)\s+([^\s]*\.xlsx?)',
                r'(?:create|make)\s+(?:excel\s+)?file\s+([^\s]+)'
            ],
            'create_directory': [
                r'(?:создай|создать)\s+(?:папку|директорию)\s+([^\s]+)',
                r'новая\s+папка\s+([^\s]+)',
                r'(?:create\s+folder|make\s+directory|mkdir)\s+([^\s]+)'
            ],
            'list_directory': [
                r'покажи\s+файлы',
                r'список\s+файлов',
                r'что\s+в\s+папке',
                r'содержимое\s+папки\s*([^\s]*)',
                r'(?:ls|dir)\s*([^\s]*)',
                r'list\s+files'
            ],
            'read_file': [
                r'(?:покажи|читай|прочитай|открой|read|show|cat)\s+(?:файл|содержимое)?\s*([^\s]+)',
            ],
            'delete_file': [
                r'(?:удали|удалить|убери|delete|remove|rm)\s+(?:файл)?\s*(.+)',
            ],
            'search': [
                r'(?:найди|поиск|ищи|search|find)\s+(.+)',
            ],
            'web_search': [
                r'(?:найди\s+в\s+интернете|поиск\s+в\s+сети|гугли|web\s+search|google)\s+(.+)',
            ]
        }
    
    def analyze_intent(self, user_input: str) -> Tuple[str, Dict[str, Any]]:
        """
        Анализ намерений пользователя и извлечение параметров
        
        Args:
            user_input: Ввод пользователя
            
        Returns:
            Tuple[intent, parameters]
        """
        user_input_lower = user_input.lower().strip()
        
        # Проверяем контекстные ссылки на предыдущие варианты
        if self._is_context_reference(user_input_lower):
            return self._handle_context_reference(user_input_lower)
        
        # Поиск совпадений по паттернам
        for intent, pattern_list in self.intent_patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, user_input_lower)
                if match:
                    groups = match.groups()
                    if groups:
                        # Находим последнюю непустую группу, которая обычно и является целью
                        target = next((g for g in reversed(groups) if g is not None), None)
                    else:
                        target = None
                    # Очищаем target от лишних слов
                    if target:
                        target = target.strip()
                        # Убираем слова-паразиты
                        target = re.sub(r'^(файл|файла|file)\s+', '', target)
                        target = re.sub(r'^(папку|папка|folder|directory)\s+', '', target)
                    
                    params = {'target': target}
                    
                    # Дополнительный анализ для извлечения контента
                    if intent == 'create_file':
                        content_match = re.search(
                            r'с содержимым\s+(.+)|с текстом\s+(.+)|with content\s+(.+)', 
                            user_input_lower
                        )
                        if content_match:
                            params['content'] = (content_match.group(1) or 
                                               content_match.group(2) or 
                                               content_match.group(3))
                    
                    if self.debug_mode:
                        logger.info(f"🎯 Найдено совпадение: паттерн='{pattern}', "
                                  f"намерение='{intent}', параметры={params}")
                    return intent, params
        
        # Если точное намерение не найдено, попробуем определить по ключевым словам
        fallback_intent = self._analyze_fallback_keywords(user_input_lower)
        if fallback_intent:
            return fallback_intent
        
        return 'general', {}
    
    def _analyze_fallback_keywords(self, user_input_lower: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Анализ по ключевым словам как fallback"""
        keyword_patterns = [
            (['файл', 'file'], ['создай', 'create', 'новый'], 'create_file'),
            (['папка', 'folder', 'директория', 'directory'], ['создай', 'create', 'новая'], 'create_directory'),
            (['читай', 'read', 'покажи', 'show', 'открой'], [], 'read_file'),
            (['удали', 'delete', 'убери', 'remove'], [], 'delete_file'),
            (['список', 'файлы', 'содержимое', 'ls', 'dir'], [], 'list_directory'),
        ]
        
        for primary_words, secondary_words, intent in keyword_patterns:
            has_primary = any(word in user_input_lower for word in primary_words)
            has_secondary = not secondary_words or any(word in user_input_lower for word in secondary_words)
            
            if has_primary and has_secondary:
                return intent, {'target': None}
        
        return None
    
    def _is_context_reference(self, user_input: str) -> bool:
        """Проверяет, является ли ввод ссылкой на предыдущий контекст"""
        # Числовые ссылки на варианты (1, 2, 3, 4)
        if user_input in ['1', '2', '3', '4', '5']:
            return True
        
        # Ключевые слова для ссылок на контекст (только короткие фразы)
        context_keywords = [
            'первый', 'второй', 'третий', 'четвертый', 'пятый',
            'первый вариант', 'второй вариант', 'третий вариант',
            'да', 'давай', 'сделай это', 'выполни'
        ]
        
        # Проверяем только если это короткая фраза (не более 2 слов) и не содержит имена файлов
        if len(user_input.split()) <= 2 and not any(ext in user_input for ext in ['.', 'файл']):
            return any(keyword in user_input for keyword in context_keywords)
        
        # Специальные случаи для переименования только если есть контекст удаления
        if len(user_input.split()) <= 2 and any(word in user_input for word in ['переименуй']):
            return self.context_memory.get('last_intent') == 'delete_file'
        
        return False
    
    def _handle_context_reference(self, user_input: str) -> Tuple[str, Dict[str, Any]]:
        """Обрабатывает ссылки на предыдущий контекст"""
        last_intent = self.context_memory.get('last_intent')
        last_params = self.context_memory.get('last_params', {})
        last_suggestions = self.context_memory.get('last_suggestions', [])
        
        # Если это числовая ссылка на вариант
        if user_input in ['1', '2', '3', '4', '5']:
            option_num = int(user_input) - 1
            
            if last_intent == 'delete_file' and last_suggestions:
                target_file = last_params.get('target')
                
                if option_num == 0:  # Переименовать файл
                    return 'move_file', {
                        'target': target_file,
                        'action': 'rename_to_backup',
                        'context_action': 'rename_for_deletion'
                    }
                elif option_num == 1:  # Переместить в папку для удаления
                    return 'move_file', {
                        'target': target_file,
                        'action': 'move_to_delete_folder',
                        'context_action': 'move_for_deletion'
                    }
                elif option_num == 2:  # Очистить содержимое
                    return 'write_file', {
                        'target': target_file,
                        'content': '',
                        'context_action': 'clear_content'
                    }
        
        # Если это текстовая ссылка на переименование
        if any(word in user_input for word in ['переименуй', 'rename']):
            if last_intent == 'delete_file':
                return 'move_file', {
                    'target': last_params.get('target'),
                    'action': 'rename_to_backup',
                    'context_action': 'rename_for_deletion'
                }
        
        # Если это общая ссылка на выполнение действия
        if any(word in user_input for word in ['да', 'давай', 'сделай', 'выполни']):
            if last_intent and last_params:
                return last_intent, last_params
        
        return 'general', {'context_reference': True, 'original_input': user_input}
    
    def update_context_memory(self, intent: str, params: Dict[str, Any], response: Any = None):
        """Обновление контекстной памяти"""
        self.context_memory.update({
            'last_intent': intent,
            'last_params': params,
            'last_response': response
        })
        
        if self.debug_mode:
            logger.debug(f"Обновлена контекстная память: intent={intent}, params={params}")
    
    def get_context_memory(self) -> Dict[str, Any]:
        """Получение контекстной памяти"""
        return self.context_memory.copy()
    
    def clear_context_memory(self):
        """Очистка контекстной памяти"""
        self.context_memory.clear()
        if self.debug_mode:
            logger.debug("Контекстная память очищена")