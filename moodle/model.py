import abc
import logging
import os
import pathlib
import time
from typing import Union

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support.select import Select

from moodle.utility import config

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

        #
        # inside settings page
        #

        # expand all settings section
        self.driver.find_element_by_class_name("collapseexpand").click()

        # expand all settings sections (more elements...)
        elements = self.driver.find_elements_by_css_selector(".moreless-toggler")
        for element in elements:
            element.click()
            time.sleep(0.5)

        # inserimento nome della lezione
        self.driver.find_element_by_id("id_name").send_keys(self.name)
        time.sleep(1)

        # controllo del flusso
        # -> revisione si
        select = Select(self.driver.find_element_by_id("id_modattempts"))
        select.select_by_index(1)
        time.sleep(1)

        # -> max tentativi 10
        select = Select(self.driver.find_element_by_id("id_maxattempts"))
        select.select_by_index(0)
        time.sleep(1)

        # valutazione
        # riprovare la lezione si
        select = Select(self.driver.find_element_by_id("id_retake"))
        select.select_by_index(1)
        time.sleep(1)

        # valutazione ripetizioni -> voto migliore
        select = Select(self.driver.find_element_by_id("id_usemaxgrade"))
        select.select_by_index(1)
        time.sleep(1)

        # completamento attività
        # -> considera completata in base a condizioni
        select = Select(self.driver.find_element_by_id("id_completion"))
        select.select_by_index(2)
        time.sleep(1)

        # END
        # submit edits and return to course page
        self.driver.find_element_by_id("id_submitbutton2").click()
        time.sleep(1.5)

        # then get its id from last module created in this section
        module_element = self.section_element.find_elements_by_css_selector(
            self.css_selector
        )[-1]
        self.dom_id = module_element.get_attribute("id")

    def upload(self, file: Union[str, os.PathLike]):
        # click upload image button
        self.driver.find_element_by_css_selector(".atto_image_button").click()
        time.sleep(2)

        # browse to desktop
        self.driver.find_element_by_css_selector(".openimagebrowser").click()
        time.sleep(2)

        # select file upload from left menu
        self.driver.find_element_by_css_selector(
            ".fp-repo-area > div:nth-child(4)"
        ).click()
        time.sleep(2)

        # find input and upload str-file (path)
        file = pathlib.Path(file)
        self.driver.find_element_by_name("repo_upload_file").send_keys(
            str(file.resolve())
        )
        time.sleep(2)

        # upload button
        self.driver.find_element_by_css_selector(".fp-upload-btn").click()
        time.sleep(2)

        # descrizione non necessaria
        self.driver.find_element_by_id(
            "id_contents_editor_atto_image_presentation"
        ).click()
        time.sleep(2)

        # cambiare size?
        # width input field id: id_contents_editor_atto_image_widthentry
        # height input field id: id_contents_editor_atto_image_heightentry

        # save image
        self.driver.find_element_by_css_selector(".atto_image_urlentrysubmit").click()

    def populate(
        self,
        directory: Union[str, os.PathLike],
        extension: str = ".png",
        prefix: str = "Slide",
    ):
        module_id = self.dom_id.split("-")[1]
        url = config["site"]["module"] + module_id
        self.driver.get(url)
        time.sleep(1)

        directory = pathlib.Path(directory)
        slides = list(
            sorted(
                directory.glob(f"*{extension}"),
                key=lambda el: int(el.stem.replace(prefix, "")),
            )
        )

        logger.info(f"Slides are {slides}")

        for i, slide in enumerate(slides):
            name = slide.stem

            logger.info(f"Sto caricando la slide {name}")

            # prima slides
            if i == 0:
                s = ".box.py-3.generalbox.firstpageoptions > p:nth-child(4) > a"
                self.driver.find_element_by_css_selector(s).click()
            else:
                # select dropdown options
                # 0 -> placeholder
                # 1 -> Aggiungi fine gruppo
                # 2 -> Aggiungi gruppo
                # 3 -> Aggiungi fine diramazione
                # 4 -> Aggiungi pagina con contenuto
                # 5 -> Aggiungi pagina con domanda

                current_url = self.driver.current_url

                max_retry = 5
                for j in range(max_retry):
                    logger.info(f"Retry {j+1}/{max_retry}")
                    select = self.driver.find_element_by_css_selector(
                        ".custom-select.singleselect"
                    )
                    Select(select).select_by_index(4)
                    time.sleep(1)

                    if self.driver.current_url != current_url:
                        logger.info("Page changed!")
                        break
                    else:
                        logger.info("Page didn't change, retry again...")
                        self.driver.refresh()

                if self.driver.current_url == current_url:
                    msg = "Redirect after clicking select option didn't work!"
                    logger.error(msg)
                    raise RuntimeError(msg)

            # sono nella pagina di inserimento Pagina con contenuto
            self.driver.find_element_by_id("id_title").send_keys(name)
            time.sleep(1)

            # espandi tutte le sezioni (bottoni)
            self.driver.find_element_by_css_selector(".collapseexpand").click()
            time.sleep(1)

            # faccio l'upload della slide
            self.upload(slide)
            time.sleep(1)

            # e ora lavoro sui bottoni
            first_input = "id_answer_editor_0"
            second_input = "id_answer_editor_1"

            first_select = "id_jumpto_0"
            second_select = "id_jumpto_1"

            # select options index
            # 0 -> Questa pagina
            # 1 -> Pagina successiva
            # 2 -> Pagina precedente
            # 3 -> Fine della lezione
            # 4 -> Domanda non vista in una pagina con contenuto
            # 5 -> Domanda casuale all'interno di una pagina di contenuto
            # 6 -> Pagina casuale con contenuto

            # prima pagina = solo avanti va popolato
            if i == 0:
                logger.info("Prima slide = popolo solo 'avanti'")

                self.driver.find_element_by_id(first_input).send_keys("Avanti")
                time.sleep(1)

                select = self.driver.find_element_by_id(first_select)
                Select(select).select_by_index(1)
                time.sleep(1)
            # sto nel mezzo
            elif i < len(slides) - 1:
                logger.info("Slide generica = popolo 'avanti' e 'indietro'")

                self.driver.find_element_by_id(first_input).send_keys("Indietro")
                time.sleep(1)

                select = self.driver.find_element_by_id(first_select)
                Select(select).select_by_index(2)
                time.sleep(1)

                self.driver.find_element_by_id(second_input).send_keys("Avanti")
                time.sleep(1)

                select = self.driver.find_element_by_id(second_select)
                Select(select).select_by_index(1)
                time.sleep(1)
            # sto all'ultima slides
            else:
                logger.info("Ultima slide = popolo solo 'indietro'")

                self.driver.find_element_by_id(first_input).send_keys("Indietro")
                time.sleep(1)

                select = self.driver.find_element_by_id(first_select)
                Select(select).select_by_index(2)
                time.sleep(1)

            # and then save slide
            self.driver.find_element_by_id("id_submitbutton").click()
            time.sleep(1)
