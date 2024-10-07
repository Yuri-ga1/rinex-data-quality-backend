import logging
import sys

class Logger:
    __default_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    __root_logger = logging.getLogger("rinex_data_quality_logger")
    
    def __init__(
            self,
            filename: str,
            file_logging_level=logging.INFO,
            console_logging: bool = False,
            console_logging_level=logging.DEBUG,
        ):
        self.__root_logger.setLevel(min(file_logging_level, console_logging_level))

        file_handler = logging.FileHandler(filename)
        file_handler.setLevel(file_logging_level)
        file_formatter = logging.Formatter(self.__default_format)
        file_handler.setFormatter(file_formatter)

        if not self._file_handler_exists(filename):
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
