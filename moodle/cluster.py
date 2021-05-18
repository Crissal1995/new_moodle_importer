import json
import os
from typing import Sequence, Union


class Answer:
    def __init__(self, json_dict: dict):
        self.is_correct: bool = json_dict["is_correct"]
        self.text: str = json_dict["text"]
        self.html: str = json_dict["html"]


class Question:
    def __init__(self, json_dict: dict):
        self.name: str = json_dict["name"]
        self.number: int = json_dict["number"]
        self.jump2slide: int = json_dict["jump2slide"]
        self.answers: Sequence[Answer] = [Answer(obj) for obj in json_dict["answers"]]


class Cluster:
    def __init__(self, json_dict: dict):
        self.min_slide_in_cluster: int = json_dict["min_slide_in_cluster"]
        self.max_slide_in_cluster: int = json_dict["max_slide_in_cluster"]
        self.questions: Sequence[Question] = [
            Question(obj) for obj in json_dict["questions"]
        ]


class ModuleCluster:
    def __init__(self, json_fp: Union[str, os.PathLike]):
        json_dict: dict = json.load(open(json_fp))
        self.clusters: Sequence[Cluster] = [
            Cluster(obj) for obj in json_dict["clusters"]
        ]
