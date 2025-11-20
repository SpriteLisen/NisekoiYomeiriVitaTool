import sys


assert sys.version_info >= (3, 7), "Python 3.7 or higher is required"

TAG_SUCCEED = "[SUCC]: "
TAG_PROGRESS = "[PROG]: "
TAG_INFO = "[INFO]: "
TAG_ERR = "[ERRO]: "
TAG_WARN = "[Warn]: "
TAG_SAME = "[SAME]: "
TAG_DIFF = "[DIFF]: "

RESET = "\033[0m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLACK = "\033[90m"
GREEN = "\033[92m"
MAGENTA = "\033[35m"


def log_succeed(msg):
    print(f"{GREEN}{TAG_SUCCEED} {msg}{RESET}")


def log_prog(msg):
    print(f"{MAGENTA}{TAG_PROGRESS} {msg}{RESET}")


def log_info(msg):
    # print(f"{BLACK}{TAG_INFO} {msg}{RESET}")
    print(f"{TAG_INFO} {msg}")


def log_warn(msg):
    print(f"{YELLOW}{TAG_WARN} {msg}{RESET}")


def log_error(msg):
    print(f"{RED}{TAG_ERR} {msg}{RESET}")


def log_same(msg):
    print(f"{GREEN}{TAG_SAME} {msg}{RESET}")


def log_diff(msg):
    print(f"{RED}{TAG_DIFF} {msg}{RESET}")