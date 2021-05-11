import argparse
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
    parser = argparse.ArgumentParser()

    # set root of data files
    root = pathlib.Path("data")
    parser.add_argument(
        "--path", help=f"The path to slides directory. Defaults to {root}", default=root
    )

    # set mutually exclusive action
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--upload-all",
        action="store_true",
        help="Create and upload all slides found in path",
    )
    group.add_argument(
        "--upload-module", action="store_true", help="Upload slides for selected module"
    )

    parser.add_argument(
        "-m",
        "--module",
        help="Specify the module id (in DOM) to use. If missing, create it.",
    )
    parser.add_argument(
        "--start-slide", type=int, help="Specify the first slide to upload"
    )
    parser.add_argument("-v", "--verbose", help="Increase verbosity")

    # parse command line args
    args = parser.parse_args()

    # increase verbosity
    if args.verbose:
        stream_handler.setLevel(logging.DEBUG)

    # get root path
    path = pathlib.Path(args.path)
    logger.info(f"Slides will be parsed from {path}")

    # test if env is correctly set
    test_environment(**kwargs)

    # create an automator object
    automator = moodle.Automator()

    if args.upload_all:
        # return directories inside path
        uf_directories = get_directories(root=args.path)

        for uf_dir in uf_directories:
            logger.info(f"UF directory: {uf_dir}")
            # create section with name of uf directory
            section = automator.create_section(uf_dir.name)

            # for every dir inside uf
            for mod_dir in get_directories(uf_dir):
                logger.info(f"MOD directory: {mod_dir}")
                # create module
                module = automator.create_module(mod_dir.name, section=section)
                # and populate it
                module.populate(mod_dir)
    elif args.upload_module:
        # if module is specified, try to get it from page
        if args.module:
            module_id = int(args.module)
            logger.info(f"Module id specified: {module_id}, will try to get it")
            module = automator.get_module(module_id=module_id)
            logger.info(f"Module found: {module}")
        # otherwise create a module inside last section, and populate it
        else:
            logger.info(
                "Module id not specified, so I will create a module inside last section"
            )
            last_section = automator.get_last_section()
            logger.info(f"Last section: {last_section}")
            module = automator.create_module(path.name, last_section)
            logger.info(f"Module created: {module}")
        start_slide = int(args.start_slide) if args.start_slide else None
        module.populate(args.path, start=start_slide)
        logger.info("Module populated with slides!")


if __name__ == "__main__":
    main()
