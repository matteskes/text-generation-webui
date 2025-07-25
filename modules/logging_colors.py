<<<<<<< Updated upstream
import logging

logger = logging.getLogger('text-generation-webui')


def setup_logging():
    '''
    Copied from: https://github.com/vladmandic/automatic

    All credits to vladmandic.
    '''

    class RingBuffer(logging.StreamHandler):
        def __init__(self, capacity):
            super().__init__()
            self.capacity = capacity
            self.buffer = []
            self.formatter = logging.Formatter('{ "asctime":"%(asctime)s", "created":%(created)f, "facility":"%(name)s", "pid":%(process)d, "tid":%(thread)d, "level":"%(levelname)s", "module":"%(module)s", "func":"%(funcName)s", "msg":"%(message)s" }')

        def emit(self, record):
            msg = self.format(record)
            # self.buffer.append(json.loads(msg))
            self.buffer.append(msg)
            if len(self.buffer) > self.capacity:
                self.buffer.pop(0)

        def get(self):
            return self.buffer

    from rich.console import Console
    from rich.logging import RichHandler
    from rich.pretty import install as pretty_install
    from rich.theme import Theme
    from rich.traceback import install as traceback_install

    level = logging.DEBUG
    logger.setLevel(logging.DEBUG)  # log to file is always at level debug for facility `sd`
    console = Console(log_time=True, log_time_format='%H:%M:%S-%f', theme=Theme({
        "traceback.border": "black",
        "traceback.border.syntax_error": "black",
        "inspect.value.border": "black",
    }))
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s | %(name)s | %(levelname)s | %(module)s | %(message)s', handlers=[logging.NullHandler()])  # redirect default logger to null
    pretty_install(console=console)
    traceback_install(console=console, extra_lines=1, max_frames=10, width=console.width, word_wrap=False, indent_guides=False, suppress=[])
    while logger.hasHandlers() and len(logger.handlers) > 0:
        logger.removeHandler(logger.handlers[0])

    # handlers
    rh = RichHandler(show_time=True, omit_repeated_times=False, show_level=True, show_path=False, markup=False, rich_tracebacks=True, log_time_format='%H:%M:%S-%f', level=level, console=console)
    rh.setLevel(level)
    logger.addHandler(rh)

    rb = RingBuffer(100)  # 100 entries default in log ring buffer
    rb.setLevel(level)
    logger.addHandler(rb)
    logger.buffer = rb.buffer

    # overrides
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("diffusers").setLevel(logging.ERROR)
    logging.getLogger("torch").setLevel(logging.ERROR)
    logging.getLogger("lycoris").handlers = logger.handlers


setup_logging()
=======
# Copied from https://stackoverflow.com/a/1336640

import logging
import platform

logging.basicConfig(
    format='%(asctime)s %(levelname)s:%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


def add_coloring_to_emit_windows(fn):
    # add methods we need to the class
    def _out_handle(self):
        import ctypes
        return ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
    out_handle = property(_out_handle)

    def _set_color(self, code):
        import ctypes

        # Constants from the Windows API
        self.STD_OUTPUT_HANDLE = -11
        hdl = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
        ctypes.windll.kernel32.SetConsoleTextAttribute(hdl, code)

    setattr(logging.StreamHandler, '_set_color', _set_color)

    def new(*args):
        FOREGROUND_BLUE = 0x0001  # text color contains blue.
        FOREGROUND_GREEN = 0x0002  # text color contains green.
        FOREGROUND_RED = 0x0004  # text color contains red.
        FOREGROUND_INTENSITY = 0x0008  # text color is intensified.
        FOREGROUND_WHITE = FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_RED
        # winbase.h
        # STD_INPUT_HANDLE = -10
        # STD_OUTPUT_HANDLE = -11
        # STD_ERROR_HANDLE = -12

        # wincon.h
        # FOREGROUND_BLACK = 0x0000
        FOREGROUND_BLUE = 0x0001
        FOREGROUND_GREEN = 0x0002
        # FOREGROUND_CYAN = 0x0003
        FOREGROUND_RED = 0x0004
        FOREGROUND_MAGENTA = 0x0005
        FOREGROUND_YELLOW = 0x0006
        # FOREGROUND_GREY = 0x0007
        FOREGROUND_INTENSITY = 0x0008  # foreground color is intensified.

        # BACKGROUND_BLACK = 0x0000
        # BACKGROUND_BLUE = 0x0010
        # BACKGROUND_GREEN = 0x0020
        # BACKGROUND_CYAN = 0x0030
        # BACKGROUND_RED = 0x0040
        # BACKGROUND_MAGENTA = 0x0050
        BACKGROUND_YELLOW = 0x0060
        # BACKGROUND_GREY = 0x0070
        BACKGROUND_INTENSITY = 0x0080  # background color is intensified.

        levelno = args[1].levelno
        if (levelno >= 50):
            color = BACKGROUND_YELLOW | FOREGROUND_RED | FOREGROUND_INTENSITY | BACKGROUND_INTENSITY
        elif (levelno >= 40):
            color = FOREGROUND_RED | FOREGROUND_INTENSITY
        elif (levelno >= 30):
            color = FOREGROUND_YELLOW | FOREGROUND_INTENSITY
        elif (levelno >= 20):
            color = FOREGROUND_GREEN
        elif (levelno >= 10):
            color = FOREGROUND_MAGENTA
        else:
            color = FOREGROUND_WHITE
        args[0]._set_color(color)

        ret = fn(*args)
        args[0]._set_color(FOREGROUND_WHITE)
        # print "after"
        return ret
    return new


def add_coloring_to_emit_ansi(fn):
    # add methods we need to the class
    def new(*args):
        levelno = args[1].levelno
        if (levelno >= 50):
            color = '\x1b[31m'  # red
        elif (levelno >= 40):
            color = '\x1b[31m'  # red
        elif (levelno >= 30):
            color = '\x1b[33m'  # yellow
        elif (levelno >= 20):
            color = '\x1b[32m'  # green
        elif (levelno >= 10):
            color = '\x1b[35m'  # pink
        else:
            color = '\x1b[0m'  # normal
        args[1].msg = color + args[1].msg + '\x1b[0m'  # normal
        # print "after"
        return fn(*args)
    return new


if platform.system() == 'Windows':
    # Windows does not support ANSI escapes and we are using API calls to set the console color
    logging.StreamHandler.emit = add_coloring_to_emit_windows(logging.StreamHandler.emit)
else:
    # all non-Windows platforms are supporting ANSI escapes so we use them
    logging.StreamHandler.emit = add_coloring_to_emit_ansi(logging.StreamHandler.emit)
    # log = logging.getLogger()
    # log.addFilter(log_filter())
    # //hdlr = logging.StreamHandler()
    # //hdlr.setFormatter(formatter())

logger = logging.getLogger('text-generation-webui')
logger.setLevel(logging.DEBUG)
>>>>>>> Stashed changes
