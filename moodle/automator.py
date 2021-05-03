import logging

from moodle.model import Section
from moodle.pages import LoginPage, ToggleEditPage
from moodle.utility import config, get_driver

logger = logging.getLogger(__name__)


class Automator:
    def __init__(self, *, wait_s: int = 3):
        if wait_s <= 0:
            msg = "Implicit wait must be positive!"
            logger.error(msg)
            raise ValueError(msg)

        driver = get_driver()
        driver.implicitly_wait(wait_s)
        self.driver = driver

        # create counter for created sections
        self.section_counter = 0
        self.unnamed_section_counter = 0

        # execute login on moodle platform
        self.login()

        # enable course edit
        self.enable_edit()

    def login(self):
        LoginPage(self.driver).complete()

    def go_to_course(self):
        self.driver.get(config["site"]["course"])

    def enable_edit(self):
        ToggleEditPage(self.driver).complete()
        logger.info("Edit course enabled")

    def create_section(self, name: str = None) -> Section:
        """Create section and returns its name"""
        return Section(name, self.driver).create()
