# AI assistance: ChatGPT (OpenAI).
# Prompt: "Improve the Toronto exam-timetabling benchmark
# downloader and loader using the project's core.py contract."

from pathlib import Path
from urllib.request import urlretrieve
from zipfile import ZipFile
import numpy as np

from core import instance_from_students

TORONTO_URL = "https://people.cs.nott.ac.uk/pszrq/files/II.zip"



SLOTS = {
    "car-s-91": 35,
    "car-f-92": 32,
    "ear-f-83": 24,
    "hec-s-92": 18,
    "kfu-s-93": 20,
    "lse-f-91": 18,
    "pur-s-93": 42,
    "rye-s-93": 23,
    "sta-f-83": 13,
    "tre-s-92": 23,
    "uta-s-92": 35,
    "ute-s-92": 10,
    "yor-f-83": 21,
}


def download_toronto(directory):
    """Download and extract the public Toronto dataset."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    archive = directory / "Toronto.zip"

    if not archive.exists():
        urlretrieve(TORONTO_URL, archive)

    with ZipFile(archive) as zipped:
        zipped.extractall(directory)

    return directory

def load_toronto(directory, name="uta-s-92"):
    """Read Toronto student registrations into a core Instance."""
    directory = Path(directory)
    name = name.lower()

    if name not in SLOTS:
        raise ValueError(f"Unknown Toronto instance: {name}")

    crs_files = list(directory.rglob("*.crs"))
    stu_files = list(directory.rglob("*.stu"))

    crs = next(
        (p for p in crs_files if p.stem.lower() in (name, name + "-2")),
        None,
    )
    stu = next(
        (p for p in stu_files if p.stem.lower() in (name, name + "-2")),
        None,
    )

    if crs is None or stu is None:
        raise FileNotFoundError(
            f"Missing .crs or .stu files for {name}"
        )

    exam_ids = []
    for line in crs.read_text().splitlines():
        if line.strip():
            exam_ids.append(line.split()[0])

    exam_to_index = {
        exam_id: i for i, exam_id in enumerate(exam_ids)
    }

    students = []
    for line in stu.read_text().splitlines():
        if line.strip():
            exams = list(dict.fromkeys(line.split()))
            students.append(
                np.array(
                    [exam_to_index[e] for e in exams],
                    dtype=np.int32,
                )
            )

    return instance_from_students(
        students,
        len(exam_ids),
        SLOTS[name],
        name,
    )
