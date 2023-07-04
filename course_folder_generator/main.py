from pathlib import Path
import typer
import logging
import shutil
import utils
import os
import re

logger = logging.Logger("main")
app = typer.Typer()

default_input_presentation_folder = "input_presentations"
max_retry = 5


def process_course(folder_path, output_folder, video_url_prefix):
    folder = Path(folder_path)
    subfolders = [subfolder for subfolder in folder.iterdir() if subfolder.is_dir()]
    pptx_files = [file for file in folder.iterdir() if
                  file.is_file() and file.suffix == '.pptx' and re.search(r'summar[y]?', file.stem, re.IGNORECASE)]
    mp4_files = [file for file in folder.iterdir() if file.is_file() and file.suffix == '.mp4']

    if pptx_files or mp4_files:
        # Folder has no subfolders, process the files here
        for video_file in mp4_files:
            # Perform operations on Video
            print(f"Processing MP4 file: {video_file.name}")
            video_txt_output_file = Path(output_folder) / "Video" / f"{video_file.stem}_video.txt"
            utils.generate_single_video_url(
                video_txt_output_file=video_txt_output_file,
                video_course_url_prefix=video_url_prefix,
                video_uri_path=video_file.stem)

        if not pptx_files:
            logger.warning(f"No SUMMARY file in path: {folder.resolve()}")
        else:
            for file in pptx_files:
                # Perform operations on PPTX
                print(f"Processing PPTX file: {file.name}")
                utils.generate_slides(
                    presentation=file,
                    output_folder=Path(output_folder) / "Lezioni",
                    video_course_url_prefix=video_url_prefix, video_uri_path=mp4_files[0].stem if len(mp4_files) > 0 else "")
    elif subfolders and not pptx_files and not mp4_files:
        # Folder has subfolders, recursively process each subfolder
        for subfolder in subfolders:
            # Recursively process each subfolder
            process_course(subfolder, output_folder, video_url_prefix)


@app.command(help="""
Generate lessons from course folder. Automatically find presentation SUMMARY in course folder and copy to input folder
""")
def generate_lesson_from_course_folder(course_folder: str = typer.Option(..., "--course-folder", "-c",
                                                                         help="Course folder"),
                                       output_folder: str = typer.Option("output", "--output-folder", "-o"),
                                       video_course_url_prefix: str = typer.Option(..., "--video-course-url-prefix",
                                                                                   "-v")):
    course_folder = Path(course_folder)

    process_course(course_folder, output_folder, video_course_url_prefix)
    # check = utils.check_right_number_of_summary_slides(course_folder)

    # if not check:
    #    logger.warning(f"Check number of slides and folder fail: {check}")
    # exit(-1)

    # utils.copy_presentations_to_input_folder(course_folder=course_folder, input_folder=default_input_presentation_folder)

    # Generate video_files
    # video_files = Path(course_folder).rglob("*.mp4")
    # video_uri_paths = [re.sub(r"\/UF *\d */", "", str(v).replace(str(course_folder), "").replace("\\", "/").replace(".mp4",""), 1) for v in video_files]
    # video_uri_paths = [
    #     re.sub(utils.config.get("REGEX", "video_uri_regex"), "",
    #            str(v).replace(str(course_folder), "").replace("\\", "/").replace(".mp4", ""), 1) for
    #     v in video_files]
    #
    # for video_uri_path in video_uri_paths:
    #     search_group = utils.uf_regex.search(video_uri_path)
    #     if not search_group:
    #         search_group = utils.lesson_regex.search(video_uri_path)
    #     uf = search_group.group(0)
    #     video_txt_output_file = Path(default_input_presentation_folder) / f"{uf}_video.txt"
    #     if utils.config.getboolean("MAIN", "generate_video_url"):
    #         utils.generate_video_url(video_txt_output_file=video_txt_output_file,
    #                                  video_course_url_prefix=video_course_url_prefix,
    #                                  video_uri_path=video_uri_path)
    #
    # generate_lessons_from_presentations(presentations_folder=default_input_presentation_folder,
    #                                     output_folder=output_folder,
    #                                     video_course_url_prefix=video_course_url_prefix)


@app.command(help="Generate lessons folders from folder with all presentations")
def generate_lessons_from_presentations(
        presentations_folder: str = typer.Option(..., "--input-presentation-folder", "-i",
                                                 help="Folder that contains course presentations"),
        output_folder: str = typer.Option("output", "--outputE-folder", "-o"),
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
        # PP ignore . in SVILUPPO_DELLA_STRATEGIA_DELLA_QUALITA_ICT_MONTEFORTE name folder, save the SVILUPPO_DELLA_STRATEGIA_DELLA_QUALITA_ICT_MONTEFORTE in the folder without . and add it when process end
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

        try:
            # Rename SVILUPPO_DELLA_STRATEGIA_DELLA_QUALITA_ICT_MONTEFORTE folder
            os.rename(tmp_output_folder, final_output_folder)
        except FileExistsError:
            logger.info("Folder exist remove it")
            os.rmdir(final_output_folder)
            os.rename(tmp_output_folder, final_output_folder)

        video_txt_output_file = final_output_folder / "video.txt"
        search_filename_without_summary = utils.uf_regex.search(file_name_without_summary)

        if not search_filename_without_summary:
            search_filename_without_summary = utils.lesson_regex.search(file_name_without_summary)
        uf = search_filename_without_summary.group(0)
        source_video_txt_path = Path(presentations_folder) / f"{uf}_video.txt"
        if source_video_txt_path.exists():
            shutil.copy(source_video_txt_path, video_txt_output_file)
        else:
            logger.info(f"File '{source_video_txt_path}' not exist generate video.txt file with presentation name")
            if utils.config.getboolean("MAIN", "generate_video_url"):
                utils.generate_video_url(video_txt_output_file=video_txt_output_file,
                                         video_course_url_prefix=video_course_url_prefix,
                                         video_uri_path=f"{file_name_without_summary}/{file_name_without_summary}")

        if lesson_durations:
            duration_txt_output_file = final_output_folder / "duration.txt"
            with open(duration_txt_output_file, "w") as v:
                # uf_id = re.search(r"UF(?:\.|\s)?(\d+(?:\.\d+)+)", presentation_file.stem).group(0)
                uf_id = re.search(utils.config.get("REGEX", "uf_id_regex"), presentation_file.stem).group(0)
                if uf_id in lesson_durations:
                    v.write(lesson_durations[uf_id.replace(" ", "")])
                else:
                    logger.error(f"Missing duration for {uf_id}, set default as 1")
                    v.write("1")


if __name__ == "__main__":
    app()
