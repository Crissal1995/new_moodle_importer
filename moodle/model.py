import logging
import time

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver, WebElement

logger = logging.getLogger(__name__)


class Section:
    selector = "li[class^=section]"
    counter = 0

    def __repr__(self):
        return f"Section(name={self.name}, dom_id={self.dom_id})"

    def __init__(self, name: str, driver: WebDriver):
        Section.counter += 1
        self.counter = Section.counter

        if not name:
            name = f"automator - section number {self.counter}"
        self.name = name
        self.driver = driver

        self.dom_id = None

        logger.debug(f"Created in-memory Section with name {name}")

    def _set_name(self, element: WebElement = None):
        if element is None:
            if self.dom_id:
                element = self.driver.find_element_by_id(self.dom_id)
            else:
                msg = "Cannot set name without element nor its DOM id!"
                logger.error(msg)
                raise ValueError(msg)

        span_sel = "div.content > h3 > span > span > a.quickeditlink > span"

        # enable editing
        element.find_element_by_css_selector(span_sel).click()

        # wait a little bit
        time.sleep(1)

        # then send name and save it
        field: WebElement = self.driver.switch_to.active_element
        field.send_keys(self.name)
        time.sleep(0.5)
        field.send_keys(Keys.ENTER)

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

        # get unique id for course
        self.dom_id = li.get_attribute("id")

        # rename freshly created
        self._set_name(element=li)

        logger.info(f"Section renamed to '{self.name}'")
        logger.debug(f"Created section on Moodle course with dom id: {self.dom_id}")

        return self
