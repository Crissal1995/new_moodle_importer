from typing import List, Union
from pathlib import Path
import shutil
import re
import logging
import win32com.client as win32
from docx import Document


logger = logging.Logger("utils")


def check_right_number_of_summary_slides(project_folder: Union[str, Path],
                                         summary_file_list: List[Union[str, Path]] = None,
                                         slides_r_glob_regex="*SUMMARY*.pptx"):
    project_folder = Path(project_folder)
    dir_number = sum(1 for element in project_folder.glob('**/*') if element.is_dir() and not bool(re.match(r"^UF *\d$", element.name)))
    summary_files_number = len(summary_file_list) if summary_file_list else len(list(project_folder.rglob(slides_r_glob_regex)))
    logger.debug(f"summary_files_number={summary_files_number}")
    logger.debug(f"dir_number={dir_number}")
    return dir_number == summary_files_number


def copy_presentations_to_input_folder(course_folder: Union[str, Path], slides_r_glob_regex="*SUMMARY*.pptx",
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

        submodule_match = re.search(r"UF(?:\.|\s)?(\d+(?:\.\d+)+).*", text)
        if submodule_match:
            duration_match = re.search(r"\(durata(?: es\.)?\s+(.+?)\)", text)
            if duration_match:
                lesson_durations[f"UF{submodule_match.group(1).strip().replace(' ', '')}"] = duration_match.group(1).replace("h", "")

    course_duration = int(course_duration.replace("h", ""))

    if course_duration != sum([int(v) for _,v in lesson_durations.items()]):
        raise Exception("Invalid lesson info")
    return course_duration, lesson_durations
