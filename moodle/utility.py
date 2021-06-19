import configparser
import logging
import os
import pathlib
import sys
from typing import Union

from selenium.webdriver import Chrome, Remote
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.remote_connection import ChromeRemoteConnection
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

logger = logging.getLogger(__name__)


def get_directories(root: Union[str, os.PathLike]):
    root = pathlib.Path(root)
    directories = [elem for elem in root.iterdir() if elem.is_dir()]

    if not directories:
        logger.warning(f"No directory found inside {root}")
        return []

    logger.info(f"Found {len(directories)} dirs inside {root}")
    return directories


def get_options(**kwargs):
    global config

    options = Options()
    options.add_argument("no-sandbox")
    options.add_argument("ignore-certificate-errors")
    options.add_argument("allow-running-insecure-content")
    options.add_argument("disable-dev-shm-usage")

    ua = kwargs.get("user_agent")
    if ua:
        options.add_argument(f"user-agent={ua}")

    headless = kwargs.get("headless", config["selenium"]["headless"])
    if headless:
        options.add_argument("headless")
        if sys.platform in ("win32", "cygwin"):
            # fix for windows platforms
            options.add_argument("disable-gpu")

    return options


def get_config(cfg_fp="moodle.cfg"):
    parser = configparser.ConfigParser()
    if not parser.read(cfg_fp):
        err = f"No such file or directory: {cfg_fp}"
        logger.error(err)
        raise EnvironmentError(err)

    # get selenium options
    env = parser.get("selenium", "env", fallback="local").lower()
    path = parser.get("selenium", "path", fallback="chromedriver").lower()
    url = parser.get(
        "selenium", "url", fallback="http://selenium-hub:4444/wd/hub"
    ).lower()
    headless = parser.getboolean("selenium", "headless", fallback=True)

    # get moodle options
    # credentials section
    username = parser.get("moodle:credentials", "username")
    password = parser.get("moodle:credentials", "password")

    # urls section
    login = parser.get("moodle:urls", "login")
    course = parser.get("moodle:urls", "course")
    module = parser.get("moodle:urls", "module")

    base_name = parser.get("upload:file_parameters", "base_name")
    base_name_in_course = parser.get("upload:file_parameters", "base_name_in_course")

    if any(not field for field in (username, password)):
        msg = "Username or password cannot be empty!"
        logger.error(msg)
        raise ValueError(msg)

    if env not in ("local", "remote"):
        err = "Invalid selenium env provided!"
        logger.error(err)
        raise ValueError(err)

    return {
        "credentials": dict(username=username, password=password),
        "site": dict(login=login, course=course, module=module),
        "selenium": dict(env=env, path=path, url=url, headless=headless),
        "file_parameters": dict(
            base_name_in_course=base_name_in_course, base_name=base_name
        ),
    }


# read one time and then use it
config = get_config()


def get_driver(**kwargs):
    """Get a Selenium Chromedriver. Options can be passed
    as kwargs, or in the configuration file"""
    global config

    options = get_options(**kwargs)
    path = kwargs.get("path", config["selenium"]["path"])
    url = kwargs.get("url", config["selenium"]["url"])

    env = config["selenium"]["env"]

    if env == "local":
        driver = Chrome(executable_path=path, options=options)
    elif env == "remote":
        driver = Remote(
            command_executor=ChromeRemoteConnection(remote_server_addr=url),
            desired_capabilities=DesiredCapabilities.CHROME,
            options=options,
        )
    else:
        # cannot enter this branch
        raise AssertionError

    driver.maximize_window()
    return driver


def change_user_agent(driver, new_user_agent: str):
    """Dinamically change chromedriver user-agent, and then
    assert that the change occurred.

    Raise an AssertionError if this is false."""

    cmd = "Network.setUserAgentOverride"
    cmd_args = dict(userAgent=new_user_agent)

    driver.execute("executeCdpCommand", {"cmd": cmd, "params": cmd_args})

    actual_user_agent = str(driver.execute_script("return navigator.userAgent;"))
    assert actual_user_agent == new_user_agent, "Cannot set user-agent!"
    logger.info(f"Changed user-agent to {new_user_agent}")


def test_environment(**kwargs):
    """Determine if current environment is correctly set"""

    try:
        get_driver(**kwargs).quit()
    except Exception as err:
        logger.error(str(err))
        raise err
    else:
        logger.info("Selenium driver found!")
