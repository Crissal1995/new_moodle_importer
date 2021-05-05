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

    def _get_element(self, element: WebElement = None) -> WebElement:
        if element:
            pass
        elif self.dom_id:
            element = self.driver.find_element_by_id(self.dom_id)
        else:
            msg = "Cannot set name without element nor DOM id!"
            logger.error(msg)
            raise ValueError(msg)

        return element

    def set_name(self, element: WebElement = None):
        span_sel = "a.quickeditlink"

        # enable editing
        element = self._get_element(element)
        element.find_element_by_css_selector(span_sel).click()
        time.sleep(1)

        # then send name and save it
        field: WebElement = self.driver.switch_to.active_element
        field.send_keys(self.name)
        time.sleep(1)

        field.send_keys(Keys.ENTER)
        time.sleep(1)

    def create(self):
        raise NotImplementedError

    def __repr__(self):
        return f"Element(dom_id={self.dom_id}, name={self.name})"


class Section(Element):
    css_selector = "li.section"

    def __repr__(self):
        return super().__repr__().replace("Element", "Section")

    def create(self):
        time.sleep(1)

        selector = "a[class=add-sections]"

        self.driver.find_element_by_css_selector(selector).click()
        time.sleep(1)
        logger.debug("Clicked add-section button")

        selector = "div[class=modal-footer] > button"
        self.driver.find_element_by_css_selector(selector).click()
        time.sleep(1)
        logger.info("Section created")

        # the section created is the last one, so we'll take it
        li = self.driver.find_elements_by_css_selector(self.css_selector)[-1]

        # get unique id for course
        self.dom_id = li.get_attribute("id")
        time.sleep(1)

        # rename freshly created
        self.set_name(element=li)

        logger.info(f"Section renamed to '{self.name}'")
        logger.debug(f"Created section on Moodle course with dom id: {self.dom_id}")


class Module(Element):
    css_selector = "li.activity"

    section: Section

    def __repr__(self):
        return super().__repr__().replace("Element", "Module")

    def __init__(self, driver: WebDriver, name: str, section: Section):
        super().__init__(driver, name)
        self.section = section

    @property
    def section_element(self) -> WebElement:
        """Returns a WebElement from the Section object"""
        return self.driver.find_element_by_id(self.section.dom_id)

    def create(self):
        time.sleep(1)

        # add content/resource button inside section
        create_sel = (
            "div:nth-child(4) > div:nth-child(5) > div:nth-child(1) >"
            " div:nth-child(1) > span:nth-child(1) > a:nth-child(1) > span:nth-child(2)"
        )

        # find first section, and from it its create resource button
        self.section_element.find_element_by_css_selector(create_sel).click()
        time.sleep(1)

        # in the new dialog obtained, select lesson and then submit
        self.driver.find_element_by_id("item_lesson").click()
        time.sleep(1)

        # select submit button
        self.driver.find_element_by_css_selector("input.submitbutton").click()
        time.sleep(1)

        # input name
        self.driver.find_element_by_id("id_name").send_keys(self.name)
        time.sleep(1)

        # submit edits and return to course page
        self.driver.find_element_by_id("id_submitbutton2").click()
        time.sleep(1.5)

        # then get its id from last module created in this section
        module_element = self.section_element.find_elements_by_css_selector(
            self.css_selector
        )[-1]
        self.dom_id = module_element.get_attribute("id")
