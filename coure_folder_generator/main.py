from pathlib import Path
import typer
import logging
import shutil
import utils
import os
import re
import urllib.parse
import requests

logger = logging.Logger("main")
app = typer.Typer()

default_input_presentation_folder = "input_presentations"
max_retry = 5


@app.command(help="""
Generate lessons from course folder. Automatically found presentation SUMMARY in course folder and copy to input folder
""")
def generate_lesson_from_course_folder(course_folder: str = typer.Option(..., "--course-folder", "-c",
                                                                         help="Course folder"),
                                       output_folder: str = typer.Option("output", "--output-folder", "-o"),
                                       video_course_url_prefix: str = typer.Option(..., "--video-course-url-prefix", "-v")):
    course_folder = Path(course_folder)
    check = utils.check_right_number_of_summary_slides(course_folder)

    if not check:
        logger.error(f"Check number of slides and folder fail: {check}")
        exit(-1)

    utils.copy_presentations_to_input_folder(course_folder=course_folder, input_folder=default_input_presentation_folder)
    generate_lessons_from_presentations(presentations_folder=default_input_presentation_folder, output_folder=output_folder,
                                        video_course_url_prefix=video_course_url_prefix)


@app.command(help="Generate elssons folders from folder with all presentations")
def generate_lessons_from_presentations(presentations_folder: str = typer.Option(..., "--input-presentation-folder", "-i",
                                                  help="Folder that contains course presentations"),
                                        output_folder: str = typer.Option("output", "--output-folder", "-o"),
                                        video_course_url_prefix: str = typer.Option(..., "--video-course-url-prefix", "-v")):
    presentation_files = Path(presentations_folder).rglob("*.pptx")
    output_folder = Path(output_folder)

    lesson_durations = None

    course_program_path = Path(presentations_folder + "/programma.docx")

    if course_program_path.exists():
        lesson_durations = utils.extract_duration_and_modules(course_program_path)[1]

    if not output_folder.exists():
        output_folder.mkdir(parents=True)

    for presentation_file in presentation_files:
        # PP ignore . in output name folder, save the output in the folder without . and add it when process end
        exported = False
        i = 0
        file_name_without_summary = re.sub(" *-* *SUMMARY", "", presentation_file.stem)
        while i < max_retry and not exported:
            try:
                final_output_folder = output_folder / file_name_without_summary
                tmp_output_folder = Path(str(final_output_folder.resolve()).replace(".", "-"))
                if len(presentation_file.name) > 254:
                    logger.info(f"File name is too long, copy to tmp file")
                    tmp_file = Path("tmp.pptx")
                    shutil.copy(presentation_file, tmp_file)
                    utils.export_jpg_from_presentation(tmp_file, tmp_output_folder)
                    shutil.rmtree(tmp_file)
                else:
                    utils.export_jpg_from_presentation(presentation_file, tmp_output_folder)
                exported = True
            except Exception:
                i += 1

        os.rename(tmp_output_folder, final_output_folder)
        video_txt_output_file = final_output_folder / "video.txt"
        with open(video_txt_output_file, "w") as v:
            if video_course_url_prefix[-1] != "/":
                video_course_url_prefix = video_course_url_prefix + "/"
            playlist_video_url = video_course_url_prefix + urllib.parse.quote(f"{file_name_without_summary}/{file_name_without_summary}.m3u8")
            v.write(playlist_video_url)
            response = requests.head(playlist_video_url)
            if response.status_code != 200:
                logger.error(f"Invalid playlist url: {playlist_video_url}")

        if lesson_durations:
            duration_txt_output_file = final_output_folder / "duration.txt"
            with open(duration_txt_output_file, "w") as v:
                uf_id = re.search(r"UF(?:\.|\s)?(\d+(?:\.\d+)+)", presentation_file.stem).group(0)
                if uf_id in lesson_durations:
                    v.write(lesson_durations[uf_id.replace(" ", "")])
                else:
                    logger.error(f"Missing duration for {uf_id}, set default as 1")
                    v.write("1")


if __name__ == "__main__":
    app()
