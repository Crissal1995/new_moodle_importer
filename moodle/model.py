import abc
import logging
import os
import pathlib
import re
import time
from typing import Union

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support.select import Select

from moodle.cluster import Cluster, ModuleCluster
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

    @staticmethod
    def clean_input(input_element: WebElement, count: int = 10):
        input_element.send_keys(Keys.BACKSPACE * count)

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

    slide_format = rf"{config['file_parameters']['base_name']}(\d+).png"
    pattern = re.compile(slide_format, re.I)

    def __repr__(self):
        return super().__repr__().replace("Element", "Module")

    def __init__(self, driver: WebDriver, name: str, section: Section = None):
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
        # convert path to pathlib object
        file = pathlib.Path(file)

        # click upload image button
        self.driver.find_element_by_css_selector(".atto_image_button").click()
        time.sleep(1)

        # browse to desktop
        self.driver.find_element_by_css_selector("button.openimagebrowser").click()
        time.sleep(1)

        # select file upload from left menu
        self.driver.find_element_by_css_selector(
            ".fp-repo-area > div:nth-child(4)"
        ).click()
        time.sleep(1)

        # find input and upload str-file (path)
        self.driver.find_element_by_name("repo_upload_file").send_keys(
            str(file.resolve())
        )
        time.sleep(1)

        # upload button
        self.driver.find_element_by_css_selector(".fp-upload-btn").click()
        time.sleep(1)

        # if file is already present, overwrite it
        try:
            self.driver.find_element_by_css_selector(
                ".file-picker.fp-dlg > div > button"
            ).click()
            time.sleep(1)
        except WebDriverException:
            pass

        # descrizione non necessaria
        # self.driver.find_element_by_id(
        #     "id_contents_editor_atto_image_presentation"
        # ).click()
        self.driver.find_element_by_id(
            "id_contents_editor_atto_image_altentry"
        ).send_keys(file.stem)
        time.sleep(0.5)

        # cambiare size?
        # width input field id: id_contents_editor_atto_image_widthentry
        width = self.driver.find_element_by_id(
            "id_contents_editor_atto_image_widthentry"
        )
        self.clean_input(width, count=5)
        width.send_keys("1280")
        time.sleep(0.7)

        # height input field id: id_contents_editor_atto_image_heightentry
        height = self.driver.find_element_by_id(
            "id_contents_editor_atto_image_heightentry"
        )
        self.clean_input(height, count=5)
        height.send_keys("960")
        time.sleep(0.7)

        # save image
        self.driver.find_element_by_css_selector(".atto_image_urlentrysubmit").click()

    def get_slide_index(self, slide: pathlib.Path):
        return int(self.pattern.match(slide.name).group(1))

    def safe_select_by_index(self, select: Select, select_index: int, max_retry: int = 5):
        current_url = self.driver.current_url

        for j in range(max_retry):
            logger.debug(f"Retry {j + 1}/{max_retry}")
            time.sleep(2)

            # take last select (last slide)
            select.select_by_index(select_index)
            time.sleep(2)

            if self.driver.current_url != current_url:
                logger.debug("Page changed!")
                break
            else:
                logger.debug("Page didn't change, retry again...")
                self.driver.refresh()

        if self.driver.current_url == current_url:
            msg = "Redirect after clicking select option didn't work!"
            logger.error(msg)
            raise RuntimeError(msg)

    def load_slide(self, slide: pathlib.Path, i: int, start: int = None, **kwargs):
        name = slide.stem

        logger.info(f"Uploading slide no. {i + 1}: {name}")

        try:
            s = ".box.py-3.generalbox.firstpageoptions > p:nth-child(4) > a"
            self.driver.find_element_by_css_selector(s).click()
            logger.debug("Uploaded first module slide")
        except WebDriverException:
            # select dropdown options
            # 0 -> placeholder
            # 1 -> Aggiungi fine gruppo
            # 2 -> Aggiungi gruppo
            # 3 -> Aggiungi fine diramazione
            # 4 -> Aggiungi pagina con contenuto
            # 5 -> Aggiungi pagina con domanda

            select = Select(self.driver.find_elements_by_css_selector(
                ".custom-select.singleselect"
            )[-1])
            self.safe_select_by_index(select, 4)

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
        # solo se però non abbiamo settato lo start
        if i == 0 and start is None:
            logger.debug("Prima slide = popolo solo 'avanti'")

            self.driver.find_element_by_id(first_input).send_keys("Avanti")
            time.sleep(1)

            select = self.driver.find_element_by_id(first_select)
            Select(select).select_by_index(1)
            time.sleep(1)
        elif kwargs.get("jump_to_random_content"):
            logger.debug(
                "Slide finale del cluster: popolo indietro e casuale con contenuto"
            )

            self.driver.find_element_by_id(first_input).send_keys("Indietro")
            time.sleep(1)

            select = self.driver.find_element_by_id(first_select)
            Select(select).select_by_index(2)
            time.sleep(1)

            self.driver.find_element_by_id(second_input).send_keys("Avanti")
            time.sleep(1)

            select = self.driver.find_element_by_id(second_select)
            Select(select).select_by_index(6)
            time.sleep(1)
        else:
            logger.debug("Slide generica = popolo 'avanti' e 'indietro'")

            prefix = kwargs.get("prefix", config["file_parameters"]["base_name_in_course"])

            self.driver.find_element_by_id(first_input).send_keys("Indietro")
            time.sleep(1)

            select = Select(self.driver.find_element_by_id(first_select))
            if kwargs.get("back_slide"):
                slide_number = kwargs.get("back_slide")
                slide = f"{prefix}{slide_number}"
                select.select_by_visible_text(slide)
            else:
                select.select_by_index(2)
            time.sleep(1)

            self.driver.find_element_by_id(second_input).send_keys("Avanti")
            time.sleep(1)

            select = self.driver.find_element_by_id(second_select)
            if kwargs.get("next_slide"):
                slide_number = kwargs.get("next_slide")
                slide = f"{prefix}{slide_number}"
                select.select_by_visible_text(slide)
            else:
                Select(select).select_by_index(1)
            time.sleep(1)

        # and then save slide
        self.driver.find_element_by_id("id_submitbutton").click()
        time.sleep(1)

        logger.info("Slide uploaded")

    def load_cluster(self, cluster: Cluster):
        logger.info("Inside load_cluster func!")

        prefix = config["file_parameters"]["base_name_in_course"]

        for question in cluster.questions:
            # prendi il penultimo select (sulla destra)
            select = self.driver.find_elements_by_css_selector(
                ".custom-select.singleselect"
            )[-2]

            # select add question from dropdown
            self.safe_select_by_index(Select(select), 5)
            time.sleep(1)

            # submit
            self.driver.find_element_by_id("id_submitbutton").click()
            time.sleep(1)

            # now we have to populate the question

            # first we expand all sections
            expand_all = self.driver.find_element_by_class_name("collapseexpand")
            if "collapse-all" not in expand_all.get_attribute("class"):
                expand_all.click()
                time.sleep(1)

            # then we submit the title (domanda i)
            self.driver.find_element_by_id("id_title").send_keys(
                f"Domanda {question.number}"
            )
            time.sleep(1)

            # then the question itself
            self.driver.find_element_by_id("id_contents_editoreditable").send_keys(
                question.name
            )
            time.sleep(1)

            # then populate the three answers
            index_wrong = 0
            for answer in question.answers:
                if answer.is_correct:
                    # find div of first answer
                    div = self.driver.find_elements_by_class_name(
                        "editor_atto_toolbar"
                    )[1]

                    # expand group of buttons
                    div.find_element_by_class_name("atto_collapse_button").click()
                    time.sleep(1)

                    # click html button
                    div.find_element_by_class_name("atto_html_button").click()
                    time.sleep(1)

                    # make textarea html visible
                    self.driver.execute_script(
                        "$('#id_answer_editor_0').removeAttr('style').removeAttr('hidden')"
                    )
                    time.sleep(1)
                    self.driver.find_element_by_id("id_answer_editor_0").send_keys(
                        answer.html
                    )
                    time.sleep(1)

                    # to save edits, click again html button
                    div.find_element_by_class_name("atto_html_button").click()
                    time.sleep(1)

                    # then jump to right slide
                    jump_to = cluster.min_slide_after_cluster
                    value = f"{prefix}{jump_to}"
                    select = Select(self.driver.find_element_by_id("id_jumpto_0"))
                    select.select_by_visible_text(value)
                    time.sleep(1)

                    # then set response
                    el = self.driver.find_element_by_id("id_response_editor_0editable")
                    el.send_keys("Risposta Esatta")
                    time.sleep(1)

                else:
                    index_wrong += 1

                    # send answer text (plaintext)
                    text_id = f"id_answer_editor_{index_wrong}editable"
                    self.driver.find_element_by_id(text_id).send_keys(answer.text)
                    time.sleep(1)

                    # then jump to right slide
                    jump_to = question.jump2slide
                    value = f"{prefix}{jump_to}"
                    select = Select(
                        self.driver.find_element_by_id(f"id_jumpto_{index_wrong}")
                    )
                    select.select_by_visible_text(value)
                    time.sleep(1)

                    # then set response
                    el = self.driver.find_element_by_id(
                        f"id_response_editor_{index_wrong}editable"
                    )
                    el.send_keys("Risposta Errata")
                    time.sleep(1)

            # then save question
            self.driver.find_element_by_id("id_submitbutton").click()
            time.sleep(1)

    def add_end_group(self):
        select = self.driver.find_elements_by_css_selector(
            ".custom-select.singleselect"
        )[-1]
        self.safe_select_by_index(Select(select), 1)

    def populate(self, directory: Union[str, os.PathLike], start: int = None):
        module_id = self.dom_id.split("-")[1]
        url = config["site"]["module"] + module_id
        self.driver.get(url)
        time.sleep(1)

        directory = pathlib.Path(directory)

        # take json file
        json_fp = list(directory.glob("*.json"))
        assert len(json_fp) > 0, "No json found inside module directory!"
        assert len(json_fp) == 1, "More than one json found inside module directory!"
        json_fp = json_fp[0]
        module_cluster = ModuleCluster(json_fp)

        clusters = [cluster for cluster in module_cluster.clusters]
        max_slide_in_cluster_list = [
            cluster.max_slide_in_cluster for cluster in clusters
        ]
        min_slide_after_cluster_list = [
            cluster.min_slide_after_cluster for cluster in clusters
        ]

        # shadow name
        get_index = self.get_slide_index

        # take slides
        slides = [
            slide for slide in directory.iterdir() if self.pattern.match(slide.name)
        ]
        slides = sorted(slides, key=get_index)

        if start is not None:
            slides = [slide for slide in slides if get_index(slide) >= start]
            assert any(
                get_index(slide) == start for slide in slides
            ), "No slide found with this start index!"

        logger.info(f"Found {len(slides)} slides, that are: {slides}")

        for i, slide in enumerate(slides):
            slide_number = int(self.pattern.match(slide.name).group(1))

            max_slide_in_cluster = slide_number in max_slide_in_cluster_list
            min_slide_after_cluster = slide_number in min_slide_after_cluster_list
            is_slide_after_end_group = slide_number-1 in min_slide_after_cluster_list

            kwargs = dict()
            if max_slide_in_cluster:
                kwargs.update(jump_to_random_content=True)
            if min_slide_after_cluster or is_slide_after_end_group:
                kwargs.update(back_slide=slide_number - 1)

            self.load_slide(slide, i, start=start, **kwargs)

            if min_slide_after_cluster:
                # carica domande fra slide precedente e attuale
                self.load_cluster(clusters.pop(0))
                self.add_end_group()
                # TODO aggiungere fine gruppo e back_slide per slide dopo fine gruppo

