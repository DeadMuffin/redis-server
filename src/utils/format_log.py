import logging
import sys

class ColoredFormatter(logging.Formatter):
    '''Logging Formatter to add colors and format the log messages.
    '''
    def __init__(self, fmt=None, colors=None):
        '''Initializes the ColoredFormatter with the specified format and colors.'''

        log_format = fmt if fmt else '%(asctime)s - %(levelname)s - %(message)s'
        super().__init__(log_format)
        
        # Default colors if none are provided
        default_colors = {
            'DEBUG': '\033[94m',  # Blue
            'INFO': '\033[92m',   # Green
            'WARNING': '\033[93m',  # Orange
            'ERROR': '\033[91m',  # Red
            'CRITICAL': '\033[91m',  # Red
            'RESET': '\033[0m'  # Reset
        }
        
        self.colors = colors if colors else default_colors
        
        for level, color in self.colors.items():
            if level != 'RESET':
                logging.addLevelName(getattr(logging, level), f'{color}{level}{self.colors["RESET"]}')

    def format(self, record):
        '''Formats the log record with the specified colors.'''
        # Temporarily set the log message format to include colors
        original_format = self._style._fmt
        self._style._fmt = f'{self.colors.get(record.levelname, self.colors["RESET"])}{original_format}{self.colors["RESET"]}'
        
        # Format the record using the temporary format
        result = super().format(record)
        
        # Restore the original format
        self._style._fmt = original_format
        
        return result

def setup_logging(level=logging.DEBUG, fmt=None, colors=None):
    '''Configures the root logger with the specified log level, format, and colors.
    
    Args:
        level: The log level to set for the root logger.
        fmt: The format string to use for log messages.
        colors: A dictionary mapping log levels to colors for the log messages.

    Example:
        custom_colors = {
            'DEBUG': '\033[95m',  # Magenta
            'INFO': '\033[96m',   # Cyan
            'WARNING': '\033[93m',  # Yellow
            'ERROR': '\033[91m',  # Red
            'CRITICAL': '\033[91m',  # Red
            'RESET': '\033[0m'  # Reset
        }

        setup_logging(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s', colors=custom_colors)\n
        logger = logging.getLogger('MyLogger')\n
        logger.debug('This is a debug message')\n
        logger.info('This is an info message')\n
        logger.warning('This is a warning message')\n
        logger.error('This is an error message')\n
        logger.critical('This is a critical message')\n
    '''
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(ColoredFormatter(fmt, colors))
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)






def test_colored_log():
    logger = logging.getLogger('test_logger')
    custom_colors = {
        'DEBUG': '\033[95m',  # Magenta
        'INFO': '\033[96m',   # Cyan
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',  # Red
        'CRITICAL': '\033[91m',  # Red
        'RESET': '\033[0m'  # Reset
    }

    setup_logging(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s', colors=custom_colors)
    logger = logging.getLogger('MyLogger')
    logger.debug('This is a debug message')
    logger.info('This is an info message')
    logger.warning('This is a warning message')
    logger.error('This is an error message')
    logger.critical('This is a critical message')

if __name__ == "__main__":
    test_colored_log()
