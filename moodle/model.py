import logging
import time

from selenium.webdriver import Remote as WebDriver
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)


class Section:
    selector = "li[class^=section]"
    counter = 0

    def __repr__(self):
        return f"Section(name={self.name}, counter={self.counter})"

    def __init__(self, name: str, driver: WebDriver):
        Section.counter += 1
        self.counter = Section.counter

        if not name:
            name = f"automator - section number {self.counter}"
        self.name = name
        self.driver = driver

        logger.debug(f"Created Section with name {name} and counter {self.counter}")

    def create(self) -> "Section":
        time.sleep(0.5)

        selector = "a[class=add-sections]"
        self.driver.find_element_by_css_selector(selector).click()
        time.sleep(0.5)
        logger.debug("Clicked add-section button")

        selector = "div[class=modal-footer] > button"
        self.driver.find_element_by_css_selector(selector).click()
        logger.info("Section created")

        # the section created is the last one, so we'll take it
        li = self.driver.find_elements_by_css_selector(Section.selector)[-1]

        # click the edit button, and then edit section
        # TODO fixed italian
        li.find_element_by_link_text("Modifica").click()
        time.sleep(1)
        li.find_element_by_link_text("Modifica argomento").click()

        # another page will open...
        time.sleep(1)

        input_name = self.driver.find_element_by_id("id_name_value")
        disabled = input_name.get_property("disabled")

        logger.info(f"input name, disabled value: {disabled}")

        if disabled:
            self.driver.find_element_by_id("id_name_customize").click()
            logger.info("Checkbox was disabled, it was enabled")

        time.sleep(1)
        input_name.send_keys(self.name)
        time.sleep(1)
        input_name.send_keys(Keys.ENTER)

        logger.info(f"Section renamed to '{self.name}'")
        logger.debug(f"Created section number {self.counter}")

        return self
