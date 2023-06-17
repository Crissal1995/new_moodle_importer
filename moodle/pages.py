import logging
from abc import ABC

from selenium.common import exceptions
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver

from moodle.utility import config

logger = logging.getLogger(__name__)


class Page(ABC):
    """Abstract web page to complete"""

    def __init__(self, driver: WebDriver):
        self.driver = driver

    def complete(self):
        raise NotImplementedError


class ToggleEditPage(Page):
    def complete(self):
        # assure we're on course page
        self.driver.get(config["site"]["course"])

        # click settings icon - gear
        #selector = "action-menu-toggle-2"
        #self.driver.find_element_by_id(selector).click()

        #selector = "#action-menu-2-menu > div:nth-child(2) > a"
        #self.driver.find_element_by_css_selector(selector).click()

        selector = "input[name='setmode']"
        self.driver.find_element_by_css_selector(selector).click()

        logger.debug("Toggle editing of course done")


class LoginPage(Page):
    """Login page"""

    def complete(self):
        logger.info("Login started")

        # go to login page
        self.driver.get(config["site"]["login"])

        try:
            username_field = self.driver.find_element_by_id("username")
            password_field = self.driver.find_element_by_id("password")
        except exceptions.NoSuchElementException:
            logger.warning("Was already logged in!")
        except exceptions.WebDriverException as e:
            logger.error(str(e))
            raise e
        else:
            username_field.send_keys(config["credentials"]["username"])
            password_field.send_keys(config["credentials"]["password"])
            password_field.send_keys(Keys.ENTER)
            logger.info("Logged in")
