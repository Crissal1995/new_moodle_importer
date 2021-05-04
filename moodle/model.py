import abc
import logging
import time

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver, WebElement

logger = logging.getLogger(__name__)


class Element(abc.ABC):
    """Interface for Elements created (Sections, Modules, ...)"""

    driver: WebDriver
    name: str
    dom_id: str = None

    css_selector: str = None

    def __init__(self, driver: WebDriver, name: str):
        self.driver = driver
        self.name = name

    def set_name(self, element: WebElement = None):
        if element is None:
            if self.dom_id:
                element = self.driver.find_element_by_id(self.dom_id)
            else:
                msg = "Cannot set name without element nor its DOM id!"
                logger.error(msg)
                raise ValueError(msg)

        span_sel = "a.quickeditlink"

        # enable editing
        element.find_element_by_css_selector(span_sel).click()

        # wait a little bit
        time.sleep(1)

        # then send name and save it
        field: WebElement = self.driver.switch_to.active_element
        field.send_keys(self.name)
        time.sleep(0.5)
        field.send_keys(Keys.ENTER)

    def create(self):
        raise NotImplementedError

    def __repr__(self):
        return f"Element(dom_id={self.dom_id}, name={self.name})"


class Section(Element):
    css_selector = "li[class^=section]"

    def __repr__(self):
        return super().__repr__().replace("Element", "Section")

    def create(self):
        time.sleep(0.5)

        selector = "a[class=add-sections]"
        self.driver.find_element_by_css_selector(selector).click()
        time.sleep(0.5)
        logger.debug("Clicked add-section button")

        selector = "div[class=modal-footer] > button"
        self.driver.find_element_by_css_selector(selector).click()
        logger.info("Section created")

        # the section created is the last one, so we'll take it
        li = self.driver.find_elements_by_css_selector(self.css_selector)[-1]

        # get unique id for course
        self.dom_id = li.get_attribute("id")

        # rename freshly created
        self.set_name(element=li)

        logger.info(f"Section renamed to '{self.name}'")
        logger.debug(f"Created section on Moodle course with dom id: {self.dom_id}")

        return self


class Module(Element):
    css_selector = ""
    section: Section

    def __repr__(self):
        return super().__repr__().replace("Element", "Module")

    def __init__(self, driver: WebDriver, name: str, section: Section):
        super().__init__(driver, name)
        self.section = section

    def create(self):
        ...
