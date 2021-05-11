import logging

from selenium.common.exceptions import WebDriverException

from moodle.model import Module, Section
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

        # execute login on moodle platform
        self.login()

        # enable course edit
        self.enable_edit()

    def __del__(self):
        try:
            self.driver.quit()
        except WebDriverException:
            pass
        finally:
            logger.info("Selenium driver quitted")

    def login(self):
        LoginPage(self.driver).complete()

    def go_to_course(self):
        self.driver.get(config["site"]["course"])

    def enable_edit(self):
        ToggleEditPage(self.driver).complete()
        logger.info("Edit course enabled")

    def get_last_section(self) -> Section:
        """Get last Section element"""
        li = self.driver.find_elements_by_css_selector(Section.css_selector)[-1]
        name = li.find_element_by_css_selector("div.content > h3").text.strip()
        section = Section(self.driver, name)
        section.dom_id = li.get_attribute("id")
        return section

    def get_module(self, module_id: int) -> Module:
        """Get Module element from its id"""
        module_dom_id = f"module-{module_id}"
        try:
            element = self.driver.find_element_by_id(module_dom_id)
        except WebDriverException:
            msg = f"Cannot find element with ID '{module_dom_id}'!"
            raise ValueError(msg)
        name = element.find_element_by_class_name("instancename").text
        module = Module(driver=self.driver, name=name)
        module.dom_id = module_dom_id
        return module

    def create_section(self, name: str) -> Section:
        """Create a Section with specified name and return it"""
        # ensure we're on course page
        self.go_to_course()

        section = Section(self.driver, name)
        section.create()
        return section

    def create_module(self, name: str, section: Section) -> Module:
        """Create a Module inside a Section and return it"""
        # ensure we're on course page
        self.go_to_course()

        module = Module(self.driver, name, section)
        module.create()
        return module
