import logging
import time

from selenium.webdriver.common.keys import Keys

from moodle.pages import LoginPage, ToggleEditPage
from moodle.utility import config, get_driver

logger = logging.getLogger(__name__)


class Automator:
    section_selector = "li[class^=section]"

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

        # test create section
        self.create_section("pippo baudo sei bello")
        self.create_section()  # automatic name

    def login(self):
        LoginPage(self.driver).complete()

    def go_to_course(self):
        self.driver.get(config["site"]["course"])

    def enable_edit(self):
        ToggleEditPage(self.driver).complete()
        logger.info("Edit course enabled")

    def create_section(self, name: str = None) -> str:
        """Create section and returns the text to find it again later"""
        selector = "a[class=add-sections]"
        self.driver.find_element_by_css_selector(selector).click()
        time.sleep(0.5)
        logger.debug("Clicked add-section button")

        selector = "div[class=modal-footer] > button"
        self.driver.find_element_by_css_selector(selector).click()
        logger.info("Section created")

        # the section created is the last one, so we'll take it
        li = self.driver.find_elements_by_css_selector(self.section_selector)[-1]

        # click the edit button, and then edit section
        # TODO fixed italian
        li.find_element_by_link_text("Modifica").click()
        time.sleep(1)
        li.find_element_by_link_text("Modifica argomento").click()

        # another page will open...
        time.sleep(1)

        # then we need to set the section name
        if not name:
            self.unnamed_section_counter += 1
            name = f"AUTOMATOR SECTION {self.unnamed_section_counter}"

        logger.debug(f"name used: {name}")

        input_name = self.driver.find_element_by_id("id_name_value")
        disabled = input_name.get_property("disabled")

        logger.info(f"input name, disabled value: {disabled}")

        if disabled:
            self.driver.find_element_by_id("id_name_customize").click()
            logger.info("Checkbox was disabled, it was enabled")

        time.sleep(1)
        input_name.send_keys(name)
        time.sleep(1)
        input_name.send_keys(Keys.ENTER)

        logger.info(f"Section renamed to '{name}'")

        self.section_counter += 1
        logger.debug(f"Created section number {self.section_counter}")

        return name
