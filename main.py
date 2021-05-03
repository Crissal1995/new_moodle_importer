import logging
import pathlib

import moodle
from moodle.utility import test_environment

FORMAT = "%(asctime)s :: %(levelname)s :: [%(module)s.%(funcName)s.%(lineno)d] :: %(message)s"
formatter = logging.Formatter(FORMAT)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler("main.log")
file_handler.setLevel(logging.INFO)

file_debug_handler = logging.FileHandler("main.debug.log")
file_debug_handler.setLevel(logging.DEBUG)

# set formatters and add handlers to main logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

handlers = (stream_handler, file_handler, file_debug_handler)

for handler in handlers:
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def main(**kwargs):
    # set root of data files
    root = pathlib.Path(kwargs.get("root", "data"))

    # test if env is correctly set
    test_environment(**kwargs)

    # take directories (uf_x m_x) from root
    directories = [elem for elem in root.iterdir() if elem.is_dir()]
    if not directories:
        logger.warning(f"No directory found inside {root}")
        return

    logger.info(f"Found {len(directories)} dirs inside {root}")

    # create an automator object
    automator = moodle.Automator()

    for directory in directories:
        logger.info(f"Working on {directory}")
        automator.create_section(directory.name)


if __name__ == "__main__":
    main()
