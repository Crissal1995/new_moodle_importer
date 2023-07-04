from typing import List, Union
from pathlib import Path
import shutil
import re
import os
import logging
import win32com.client as win32
from docx import Document
import urllib
import requests
import configparser

config = configparser.ConfigParser()
config.read('regex.conf')

# uf_regex = re.compile(r"UF(?:\.|\s)?(\d+(?:\.\d+)+)")
uf_regex = re.compile(config.get("REGEX", "uf_regex"))
lesson_regex = re.compile(config.get("REGEX", "lesson_regex"))
logger = logging.Logger("utils")


def check_right_number_of_summary_slides(project_folder: Union[str, Path],
                                         summary_file_list: List[Union[str, Path]] = None,
                                         slides_r_glob_regex="*SUM*.pptx"):
    project_folder = Path(project_folder)
    dir_number = sum(1 for element in project_folder.glob('**/*') if element.is_dir() and not bool(
        re.match(config.get("REGEX", "module_dir_regex"),
                 element.name)))  # and not bool(re.match(r"^UF *\d$", element.name)))
    summary_files_number = len(summary_file_list) if summary_file_list else len(
        list(project_folder.rglob(slides_r_glob_regex)))
    logger.debug(f"summary_files_numbedir={summary_files_number}")
    logger.debug(f"dir_number={dir_number}")
    return summary_files_number == dir_number


def copy_presentations_to_input_folder(course_folder: Union[str, Path], slides_r_glob_regex="*SUM*.pptx",
                                       input_folder: str = "input_presentations"):
    course_folder = Path(course_folder)
    presentation_path_list = list(course_folder.rglob(slides_r_glob_regex))
    bulk_file_copy(presentation_path_list, input_folder)


def bulk_file_copy(source_path_list: List[Union[str, Path]], output_folder_path: Union[str, Path], move: bool = False):
    output_folder_path = Path(output_folder_path)
    if not output_folder_path.exists():
        output_folder_path.mkdir()

    for source_path in source_path_list:
        s = Path(source_path)

        if config.getboolean("MAIN", "rename_output_with_folder_name"):
            o = output_folder_path / s.parent.name
        else:
            o = output_folder_path / s.name
        if move:
            shutil.move(s, o)
        else:
            shutil.copy(s, o)


def export_jpg_from_presentation(presentation_path: Union[str, Path], output_folder: Union[str, Path]):
    power_point = win32.gencache.EnsureDispatch('PowerPoint.Application')
    presentation = power_point.Presentations.Open(presentation_path.resolve(), False)
    presentation.Export(output_folder.resolve(), "JPG")
    presentation.Close()
    power_point.Quit()


def extract_duration_and_modules(file_path):
    # Existing code for file processing

    document = Document(file_path)
    lesson_durations = {}
    course_duration = None

    paragraphs = iter(document.paragraphs)
    for paragraph in paragraphs:
        text = paragraph.text.strip()

        if text.startswith("DURATA"):
            next_paragraph = next(paragraphs, None)
            if next_paragraph:
                course_duration = next_paragraph.text.strip()

        submodule_match = uf_regex.search(text)
        if submodule_match:
            # duration_match = re.search(r"\(durata(?: es\.)?\s+(.+?)\)", text)
            duration_match = re.search(config.get("REGEX", "duration_regex"), text)
            if duration_match:
                lesson_durations[f"UF{submodule_match.group(1).strip().replace(' ', '')}"] = duration_match.group(
                    1).replace("h", "")

    course_duration = int(course_duration.replace("h", ""))
    lessons_duration = sum([int(v) for _, v in lesson_durations.items()])

    if course_duration != lessons_duration:
        # raise Exception("Invalid lesson info")
        logger.warning(f"Invalid lessons duration: {lessons_duration} - it should be: {course_duration}")
    return course_duration, lesson_durations


def modify_url(url):
    # Replace spaces and multiple spaces with '+'
    modified_url = re.sub(r'\s', '+', url)

    # URL-encode remaining special characters
    modified_url = urllib.parse.quote(modified_url, safe='+')

    return modified_url


def check_video_uri(video_uri: str):
    video_uri_parts = video_uri.split("/")
    if len(video_uri_parts) < 2:
        return True

    first = video_uri_parts[0]
    for element in video_uri_parts[1:]:
        if element != first:
            return False

    return True


def generate_video_url(video_txt_output_file: Union[str, Path], video_course_url_prefix: str, video_uri_path: str):
    with open(video_txt_output_file, "w") as v:
        if video_course_url_prefix[-1] != "/":
            video_course_url_prefix = video_course_url_prefix + "/"
        # playlist_video_url = video_course_url_prefix + urllib.parse.quote(f"{video_uri_path}.m3u8")
        if not check_video_uri(video_uri_path):
            video_uri_path = video_uri_path.split("/")[-1]
            video_uri_path += "/" + video_uri_path
        playlist_video_url = video_course_url_prefix + f"{modify_url(video_uri_path)}.m3u8"
        # playlist_video_url = video_course_url_prefix + f"{replace_spaces(video_uri_path)}.m3u8"
        v.write(playlist_video_url)
        response = requests.head(playlist_video_url)
        if response.status_code != 200:
            logger.error(f"Invalid playlist url: {playlist_video_url}")


def generate_single_video_url(video_txt_output_file: Union[str, Path], video_course_url_prefix: str,
                              video_uri_path: Union[str, Path]):
    video_txt_output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(video_txt_output_file.resolve(), mode="w") as v:
        if video_course_url_prefix[-1] != "/":
            video_course_url_prefix = video_course_url_prefix + "/"

        playlist_video_url = video_course_url_prefix + f"{modify_url(video_uri_path)}/{modify_url(video_uri_path)}.m3u8"
        # playlist_video_url = video_course_url_prefix + f"{replace_spaces(video_uri_path)}.m3u8"
        v.write(playlist_video_url)
        response = requests.head(playlist_video_url)
        if response.status_code != 200:
            logger.error(f"Invalid playlist url: {playlist_video_url}")


def generate_slides(presentation: Union[str, Path], output_folder: Union[str, Path],
                    video_course_url_prefix: Union[str, Path], video_uri_path: str, max_retry: int = 5):
    output_folder = Path(output_folder)

    if not output_folder.exists():
        output_folder.mkdir(parents=True)

    exported = False
    i = 0
    file_name_without_summary = re.sub(r'[-]?\s*summar[y]?', "", presentation.stem, flags=re.IGNORECASE)
    module_name = str(presentation.parent.parent).split("\\")[-1]
    final_output_folder = output_folder / module_name / file_name_without_summary
    final_output_folder.mkdir(parents=True, exist_ok=True)

    tmp_output_folder = Path(str(final_output_folder.resolve()).replace(".", "-"))

    while i < max_retry and not exported:
        try:
            if len(presentation.name) > 254:
                logger.info(f"File name is too long, copy to tmp file")
                tmp_file = Path("tmp.pptx")
                shutil.copy(presentation, tmp_file)
                export_jpg_from_presentation(tmp_file, tmp_output_folder)
                shutil.rmtree(tmp_file)
            else:
                export_jpg_from_presentation(presentation, tmp_output_folder)
            exported = True
        except Exception as e:
            i += 1
            logger.warning(str(e))
            logger.warning(f"Try number: {i}")

    try:
        # Rename SVILUPPO_DELLA_STRATEGIA_DELLA_QUALITA_ICT_MONTEFORTE folder
        if exported:
            os.rename(tmp_output_folder, final_output_folder)
        else:
            logger.error(f"Cannot export: {presentation}")
    except FileExistsError:
        logger.info("Folder exist remove it")
        os.rmdir(final_output_folder)
        #shutil.rmtree(final_output_folder)
        os.rename(tmp_output_folder, final_output_folder)
    except FileNotFoundError as e:
        logger.error(f"Cannot find: {tmp_output_folder}")
        logger.error(str(e))

    video_txt_output_file = final_output_folder / "video.txt"

    source_video_txt_path = output_folder / "Video" / f"{video_uri_path}_video.txt"
    if source_video_txt_path.exists():
        shutil.copy(source_video_txt_path, video_txt_output_file)
    else:
        logger.info(f"File '{source_video_txt_path}' not exist generate video.txt file with presentation name")
        if config.getboolean("MAIN", "generate_video_url") and video_uri_path:
            generate_single_video_url(
                video_txt_output_file=video_txt_output_file,
                video_course_url_prefix=video_course_url_prefix,
                video_uri_path=video_uri_path)
