"""Module to pretty print log/informational messages"""
import sys

# Set this to true to turn on debugging (i.e. do log.debug_enabled = True)
debug_enabled = False
# Enable/disable colors - default to on if we're a real terminal
if sys.stdout.isatty():
    color_enabled = True
else:
    color_enabled = False

# Ansi color lists
cesc = '\033[%d;%dm'
colors = {
    'normal':     '\033[0m',
    'black':      cesc % (0, 30),
    'red':        cesc % (0, 31),
    'green':      cesc % (0, 32),
    'yellow':     cesc % (0, 33),
    'blue':       cesc % (0, 34),
    'magenta':    cesc % (0, 35),
    'cyan':       cesc % (0, 36),
    'white':      cesc % (0, 37),
    'bblack':     cesc % (1, 30),
    'bred':       cesc % (1, 31),
    'bgreen':     cesc % (1, 32),
    'byellow':    cesc % (1, 33),
    'bblue':      cesc % (1, 34),
    'bmagenta':   cesc % (1, 35),
    'bcyan':      cesc % (1, 36),
    'bwhite':     cesc % (1, 37)}


def colorformat(s, color):
    if color_enabled:
        return " %s*%s %s" % (colors[color], colors['normal'], s)
    else:
        return " * %s" % s


def msg(s):
    print colorformat(s, 'bgreen')


def debug(s):
    if debug_enabled:
        print colorformat(s, 'bcyan')


def error(s):
    print colorformat("ERROR: %s" % s, 'bred')


def msgnb(s):
    """Emits a message with no line break"""
    sys.stdout.write(colorformat(s, 'bgreen'))
    sys.stdout.flush()


def msgnf(s):
    """Emits a message without any formatting.

    Useful for adding extra text to the end of a line output using msgnb.
    """
    print s
