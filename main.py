import logging
import pathlib

import moodle
from moodle.utility import get_directories, test_environment

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

    # get root modules (ufx)
    uf_directories = get_directories(root=root)

    # create an automator object
    automator = moodle.Automator()

    for uf_dir in uf_directories:
        logger.info(f"UF directory: {uf_dir}")
        section = automator.create_section(uf_dir.name)
        for mod_dir in get_directories(uf_dir):
            logger.info(f"MOD directory: {mod_dir}")
            module = automator.create_module(mod_dir.name, section=section)
            module.populate(mod_dir)


if __name__ == "__main__":
    main()
