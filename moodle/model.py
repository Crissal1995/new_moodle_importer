import abc
import logging
import os
import pathlib
import re
import time
from typing import Union

from selenium.common.exceptions import WebDriverException, NoSuchElementException
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

        selector = "li:last-child  a.add-sections"

        self.driver.find_element_by_css_selector(selector).click()
        time.sleep(1)
        logger.debug("Clicked add-section button")

        # selector = "div[class=modal-footer] > button"
        # self.driver.find_element_by_css_selector(selector).click()
        # time.sleep(1)
        # logger.info("Section created")

        # the section created is the last one, so we'll take it
        li = self.driver.find_elements_by_css_selector(self.css_selector)[-1]

        # get unique id for course
        self.dom_id = li.get_attribute("id")
        time.sleep(1)

        # rename freshly created
        self.set_name(element=li)

        logger.info(f"Section renamed to '{self.name}'")
        logger.debug(f"Created section on Moodle course with dom id: {self.dom_id}")


class Slide:
    base_name = config["file_parameters"]["base_name"]
    pattern = re.compile(r"[^\d]*(\d+)", re.I)

    def __init__(self, path: Union[str, os.PathLike]):
        self.path = pathlib.Path(path)
        self.name = self.path.name
        self.index = self.get_index()

    def __repr__(self):
        return f"Slide({self.path})"

    def get_index(self):
        match = self.pattern.match(self.name)
        if not match:
            raise ValueError(
                f"Cannot match {self.name} with pattern '{self.pattern.pattern}'"
            )
        return int(match.group(1))


class Module(Element):
    css_selector = "li.activity"
    section: Section

    def __repr__(self):
        return super().__repr__().replace("Element", "Module")

    def __init__(self, driver: WebDriver, name: str, section: Section = None):
        super().__init__(driver, name)
        self.section = section

    @property
    def section_element(self) -> WebElement:
        """Returns a WebElement from the Section object"""
        return self.driver.find_element_by_id(self.section.dom_id)

    def create(self, duration: str = None):
        time.sleep(1)

        # add content/resource button inside section
        # create_sel = (
        #    "div:nth-child(4) > div:nth-child(5) > div:nth-child(1) >"
        #   " div:nth-child(1) > span:nth-child(1) > a:nth-child(1) > span:nth-child(2)"
        # )

        create_sel = ".activity-add-text"

        # find first section, and from it its create resource button
        self.section_element.find_element_by_css_selector(create_sel).click()
        time.sleep(1)

        # in the new dialog obtained, select lesson and then submit
        # self.driver.find_element_by_id("item_lesson").click()
        # time.sleep(1)

        # select submit button
        # self.driver.find_element_by_css_selector("input.submitbutton").click()
        # time.sleep(1)

        selector = "div[data-internal='lesson']"
        self.driver.find_element_by_css_selector(selector).click()

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

        # completamento per l'accesso

        # aggiungi criterio
        add_criteria_btn = self.driver.find_element_by_class_name("availability-button").find_element_by_tag_name(
            "button")
        add_criteria_btn.click()
        time.sleep(1)

        # clicca completamento attività
        activity_completion_btn = self.driver.find_element_by_id("availability_addrestriction_completion")
        activity_completion_btn.click()
        time.sleep(1)

        # seleziona completamento attività precedente
        completion_selection = Select(self.driver \
                                      .find_element_by_css_selector("span.availability_completion.availability-plugincontrols") \
                                      .find_element_by_css_selector('select[name="cm"]'))
        completion_selection.select_by_index(1)
        time.sleep(1)

        # completamento attività
        # -> considera completata in base a condizioni
        select = Select(self.driver.find_element_by_id("id_completion"))
        select.select_by_index(2)
        time.sleep(1)

        # set duration
        if duration:
            self.driver.find_element_by_css_selector("div#fgroup_id_completiontimespentgroup label").click()
            time.sleep(0.5)
            select = Select(self.driver.find_element_by_id("id_completiontimespent_timeunit"))
            select.select_by_index(2)
            time.sleep(0.5)
            self.driver.find_element_by_id("id_completiontimespent_number").send_keys(duration)
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

    def upload_slide(self, file: Union[str, os.PathLike]):
        # convert path to pathlib object
        file = pathlib.Path(file)

        # click upload image button
        self.driver.find_element_by_css_selector("button[title='Image']").click()
        time.sleep(1)

        # browse to desktop
        self.driver.find_element_by_css_selector("button.openimagebrowser").click()
        time.sleep(1)

        # select file upload from left menu
        self.driver.find_element_by_css_selector(
            ".fp-repo-area > div:nth-child(5)"
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
            "id_contents_editor_tiny_image_altentry"
        ).send_keys(file.stem)
        time.sleep(0.5)

        # cambiare size?
        # width input field id: id_contents_editor_atto_image_widthentry
        width = self.driver.find_element_by_id(
            "id_contents_editor_tiny_image_widthentry"
        )
        self.clean_input(width, count=5)
        width.send_keys("1280")
        time.sleep(0.7)

        # height input field id: id_contents_editor_atto_image_heightentry
        # height = self.driver.find_element_by_id(
        #     "id_contents_editor_atto_image_heightentry"
        # )
        # self.clean_input(height, count=5)
        # height.send_keys("960")
        time.sleep(0.7)

        # save image
        self.driver.find_element_by_css_selector(".tiny_image_urlentrysubmit").click()

    def add_video_by_url(self, video_url):
        # click upload image button
        self.driver.find_element_by_css_selector("button[title='Multimedia']").click()
        time.sleep(1)

        # Aggiungo il video
        self.driver.find_element_by_css_selector("li[data-medium-type='video']").click()
        time.sleep(1)
        self.driver.find_element_by_id("video-video-url-input").send_keys(video_url)
        time.sleep(1)

        # Imposto la dimensione
        self.driver.find_element_by_css_selector("a[href='#vdisplayoptions']").click()
        time.sleep(1)
        self.driver.find_element_by_id("vdisplayoptions_media-width-entry").send_keys(1280)
        self.driver.find_element_by_id("vdisplayoptions_media-height-entry").send_keys(720)
        time.sleep(1)

        # Salvo
        self.driver.find_element_by_css_selector("div.modal-footer button.btn-primary").click()
        time.sleep(1)

    def safe_select_by_index(
            self,
            select: Select,
            select_index: int,
            max_retry: int = 10,
            *,
            raw: str,
            should_redirect: bool = True,
    ):
        current_url = self.driver.current_url
        time.sleep(1)

        for j in range(max_retry):
            logger.debug(f"Retry {j + 1}/{max_retry}")

            try:
                # take last select (last slide)
                select.select_by_index(select_index)
                time.sleep(1)
            except WebDriverException as e:
                logger.warning(f"An exception occurred: {e}")
                logger.warning("Getting again select element from raw...")
                self.driver.refresh()
                time.sleep(1)
                select = Select(eval(raw))
                continue

            if should_redirect:
                if self.driver.current_url != current_url:
                    logger.debug("Page changed!")
                    break
                else:
                    logger.debug("Page didn't change, retry again...")
                    self.driver.refresh()
            else:
                break

        if should_redirect and self.driver.current_url == current_url:
            msg = "Redirect after clicking select option didn't work!"
            raise RuntimeError(msg) from None

    def add_content_page(self, element_index: int, slide: pathlib.Path = None, start: int = None, video_url: str = None,
                         **kwargs):

        if slide:
            name = slide.stem
            logger.info(f"Uploading slide no. {element_index + 1}: {name}")
        elif video_url:
            name = f"Video {element_index + 1}"
            logger.info(f"Add video by url, no. {element_index + 1}")
        else:
            raise Exception("Slide or video url is requires.")

        try:
            s = ".box.py-3.generalbox.firstpageoptions > p:nth-child(3) > a"
            self.driver.find_element_by_css_selector(s).click()
            logger.debug("Uploaded first module slide")
        except (WebDriverException, NoSuchElementException):
            # select dropdown options
            #  -> placeholder
            #  -> Aggiungi fine gruppo
            #  -> Aggiungi gruppo
            #  -> Aggiungi fine diramazione
            # 20 -> Aggiungi pagina con contenuto
            #  -> Aggiungi pagina con domanda

            # prendi il penultimo select (l'ultimo è "Vai a ...")
            select_elems = self.driver.find_elements_by_tag_name("select")
            select = Select(select_elems[-1])
            # raw = """self.driver.find_elements_by_tag_name("select")[-2]"""
            # self.safe_select_by_index(select, 2, raw=raw)
            select.select_by_value("20")

        # sono nella pagina d'inserimento Pagina con contenuto
        name_in_course = name.replace(
            config["file_parameters"]["base_name"],
            config["file_parameters"]["base_name_in_course"],
        )
        self.driver.find_element_by_id("id_title").send_keys(name_in_course)
        time.sleep(1)

        # espandi tutte le sezioni (bottoni)
        self.driver.find_element_by_css_selector(".collapseexpand").click()
        time.sleep(1)

        if slide:
            # faccio l'upload della slide
            self.upload_slide(slide)
            time.sleep(2)
        else:
            self.add_video_by_url(video_url)

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
        if element_index == 0 and start is None and not video_url:
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
            prefix = kwargs.get(
                "prefix", config["file_parameters"]["base_name_in_course"]
            )

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

    def load_cluster(self, cluster: Cluster, **kwargs):
        logger.info("Inside load_cluster func!")

        prefix = config["file_parameters"]["base_name_in_course"]

        is_last_slide = kwargs.get("is_last_slide", False)
        slide_index = kwargs["index"]
        is_last_slide_in_cluster = slide_index <= cluster.max_slide_in_cluster

        if is_last_slide and is_last_slide_in_cluster:
            jump2correct = "Fine gruppo"
        else:
            jump_to = cluster.max_slide_in_cluster + 1
            jump2correct = f"{prefix}{jump_to}"

        for i, question in enumerate(cluster.questions):
            # when called this function, we can have two scenarios
            # 1) slide (end), end group, slide (after-end) -> we take -3
            # 2) slide (end), end group -> we take -2
            # 2 is possible when is last slide is True
            index = -3
            if is_last_slide and is_last_slide_in_cluster:
                index = -2

            select = self.driver.find_elements_by_css_selector(
                ".custom-select.singleselect"
            )[index]

            raw = f"""self.driver.find_elements_by_css_selector(
                ".custom-select.singleselect"
            )[{index}]""".strip()

            # select add question from dropdown
            self.safe_select_by_index(Select(select), 5, raw=raw)
            time.sleep(1)

            # submit
            self.driver.find_element_by_id("id_submitbutton").click()
            time.sleep(1)

            # now we have to populate the question
            name = f"Domanda {question.number}"

            logger.info(f"Uploading question no. {i + 1}: {name}")

            # first we expand all sections
            expand_all = self.driver.find_element_by_class_name("collapseexpand")
            if "collapse-all" not in expand_all.get_attribute("class"):
                expand_all.click()
                time.sleep(1)

            # then we submit the title (domanda i)
            self.driver.find_element_by_id("id_title").send_keys(name)
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

                    # select correct slide to jump
                    select = Select(self.driver.find_element_by_id("id_jumpto_0"))
                    select.select_by_visible_text(jump2correct)
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
            logger.info("Question uploaded")
            time.sleep(1)

    def add_end_group(self):
        select = self.driver.find_elements_by_css_selector(
            ".custom-select.singleselect"
        )[-1]
        raw = """self.driver.find_elements_by_css_selector(
            ".custom-select.singleselect"
        )[-1]""".strip()
        self.safe_select_by_index(Select(select), 1, raw=raw, should_redirect=False)

    def populate(
            self,
            directory: Union[str, os.PathLike],
            start: int = None,
            load_only_slide=False,
    ):
        module_id = self.dom_id.split("-")[1]
        url = config["site"]["module"] + module_id
        self.driver.get(url)
        time.sleep(1)

        directory = pathlib.Path(directory)

        # take json file
        json_fp = list(directory.glob("*.json"))
        if not load_only_slide:
            assert len(json_fp) > 0, "No json found inside module directory!"
            assert (
                    len(json_fp) == 1
            ), "More than one json found inside module directory!"
            json_fp = json_fp[0]

            # create object of all module clusters
            module_cluster = ModuleCluster(json_fp)

            # take all clusters for module as list
            clusters = [cluster for cluster in module_cluster.clusters]

            # and then take max slide in cluster (BEFORE questions)
            max_slide_in_cluster_list = [
                cluster.max_slide_in_cluster for cluster in clusters
            ]
        else:
            max_slide_in_cluster_list = []
            clusters = []

        # glob slides from directory
        # also convert to Slide objects
        slides = [
            Slide(slide)
            for slide in directory.iterdir()
            if Slide.pattern.match(slide.name) and "json" not in slide.name
        ]
        # sort them by index
        slides = sorted(slides, key=lambda slide: slide.index)

        # if start is specified, select subset of slides
        if start is not None:
            slides = [slide for slide in slides if slide.index >= start]
            assert any(
                slide.index == start for slide in slides
            ), "No slide found with this start index!"

        # filter out "wrong" clusters, the ones already created
        first_slide = slides[0]

        # take a cluster only if the first slide to upload is behind its max slide
        clusters = [
            cluster
            for cluster in clusters
            if first_slide.index <= cluster.max_slide_in_cluster
        ]

        logger.info(f"Found {len(slides)} slides, that are: {slides}")

        for i, slide in enumerate(slides):
            # ultima slide della lista delle slides da caricare
            is_last_slide = i == len(slides) - 1

            # massima slide nel cluster corrente
            max_slide_in_cluster = slide.index in max_slide_in_cluster_list

            # minima slide dopo il cluster e PRIMA del fine gruppo
            min_slide_after_cluster = slide.index - 1 in max_slide_in_cluster_list

            # minima slide dopo il cluster e DOPO del fine gruppo
            min_slide_after_end_group = slide.index - 2 in max_slide_in_cluster_list

            kwargs = dict()
            if max_slide_in_cluster:
                kwargs.update(jump_to_random_content=True)
            if min_slide_after_cluster or min_slide_after_end_group:
                kwargs.update(back_slide=slide.index - 1)

            self.add_content_page(element_index=i, slide=slide.path, start=start, **kwargs)

            # se ho l'ultima slides e ancora clusters (uno?) da caricare
            # oppure se mi trovo esattamente una slide dopo la max slide del cluster passato
            # allora carico il cluster e aggiungo fine gruppo
            if (is_last_slide and clusters) or min_slide_after_cluster:
                # create end group
                self.add_end_group()

                # carica domande fra slide precedente e attuale
                self.load_cluster(
                    clusters.pop(0), is_last_slide=is_last_slide, index=slide.index
                )

        video_txt_file_path = pathlib.Path.joinpath(directory / 'video.txt')
        if video_txt_file_path.exists():

            video_urls = open(video_txt_file_path)
            for i, video_url in enumerate(video_urls):
                self.add_content_page(element_index=i, video_url=video_url)
