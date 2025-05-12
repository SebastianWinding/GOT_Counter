import os
import sys


def get_supports_color() -> bool:
    # not a TTY? no color.
    if not sys.stdout.isatty():
        return False
    try:
        import curses
        curses.setupterm()
        # require at least 8 colors; many terminals support 256 or more
        return curses.tigetnum("colors") >= 8
    except Exception:
        return False

def get_env() -> dict:
    env = os.environ.copy()
    # if get_supports_color():
    #     # only force if we actually have a color-capable TTY
    #     env['FORCE_COLOR'] = '1'
    return env