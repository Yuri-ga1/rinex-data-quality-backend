import logging
import sys
from datetime import datetime
import os
import threading

class Logger:
    __default_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    __root_logger = logging.getLogger("rinex_data_quality_logger")
    __last_cleanup = None
    
    def __init__(
            self,
            filename: str,
            file_logging_level=logging.INFO,
            console_logging: bool = False,
            console_logging_level=logging.DEBUG,
            cleanup_interval: int = 86400,  # Интервал проверки логов в секундах (24 часа = 86400 секунд)
        ):
        self.filename = filename
        self.cleanup_interval = cleanup_interval
        self.__last_cleanup = datetime.now()
        
        self.__start_cleanup_thread()
        
        self.__root_logger.setLevel(min(file_logging_level, console_logging_level))

        file_handler = logging.FileHandler(self.filename)
        file_handler.setLevel(file_logging_level)
        file_formatter = logging.Formatter(self.__default_format)
        file_handler.setFormatter(file_formatter)

        self.__root_logger.addHandler(file_handler)

        if console_logging:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(console_logging_level)
            console_formatter = logging.Formatter(self.__default_format)
            console_handler.setFormatter(console_formatter)
            self.__root_logger.addHandler(console_handler)

    def _file_handler_exists(self, filename: str) -> bool:
        """Проверка, существует ли уже файловый обработчик."""
        for handler in self.__root_logger.handlers:
            if isinstance(handler, logging.FileHandler) and handler.baseFilename == filename:
                return True
        return False
    
    def __start_cleanup_thread(self):
        """Запуск фонового потока для периодической проверки и очистки логов."""
        def cleanup_logs_periodically():
            while True:
                current_time = datetime.now()
                # Проверяем, прошло ли больше cleanup_interval времени с последней очистки
                if (current_time - self.__last_cleanup).total_seconds() >= self.cleanup_interval:
                    self.__remove_old_logs_from_file()
                    self.__last_cleanup = current_time
                # Ждем час перед следующей проверкой
                threading.Event().wait(3600)

        # Запускаем поток очистки
        cleanup_thread = threading.Thread(target=cleanup_logs_periodically, daemon=True)
        cleanup_thread.start()

            
    def __remove_old_logs_from_file(self, days_threshold: int = 30) -> None:
        """Удаление строк логов старше определенного количества дней.
        Создание копии файла и замена оригинального на копию
        """
        if not os.path.exists(self.filename):
            return

        temp_filename = self.filename + ".tmp"
        current_time = datetime.now()

        with open(self.filename, "r") as log_file, open(temp_filename, "w") as temp_file:
            log_is_old = True

            for line in log_file:
                log_date = self.__extract_log_date(line)

                if log_date:
                    if (current_time - log_date).days <= days_threshold:
                        log_is_old = False

                if not log_is_old:
                    temp_file.write(line)

        os.replace(temp_filename, self.filename)
                
    def __extract_log_date(self, line: str) -> datetime:
        """Извлекает дату лога из строки"""
        try:
            date_str = line.split(" - ")[0]
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S,%f")
        except (IndexError, ValueError):
            return None

    # Методы для логгирования на разных уровнях
    def debug(self, message: str) -> None:
        """Логгирование на уровне DEBUG"""
        self.__root_logger.debug(message)

    def info(self, message: str) -> None:
        """Логгирование на уровне INFO"""
        self.__root_logger.info(message)

    def warning(self, message: str) -> None:
        """Логгирование на уровне WARNING"""
        self.__root_logger.warning(message)

    def error(self, message: str) -> None:
        """Логгирование на уровне ERROR"""
        self.__root_logger.error(message)

    def critical(self, message: str) -> None:
        """Логгирование на уровне CRITICAL"""
        self.__root_logger.critical(message)
