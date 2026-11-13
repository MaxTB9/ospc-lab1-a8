
# AI assistance: ChatGPT (OpenAI).
# Prompt: "help me structure code for exam-timetabling instance generator
# using NumPy and the project's instance_from_students contract, correct the code and improve its expression."

import numpy as np
from core import instance_from_students


def generate_instance(
    n_exams=200,
    n_students=1000,
    n_slots=20,
    max_exams_per_student=5,
    seed=2026,
):
    """Generate a reproducible synthetic exam-timetabling instance."""

    if n_exams < 1 or n_students < 1 or n_slots < 1:
        raise ValueError("Exams, students, and slots must be positive.")

    if max_exams_per_student < 1:
        raise ValueError("Each student must take at least one exam.")

    rng = np.random.default_rng(seed)

    students = []

    for _ in range(n_students):
        count = rng.integers(
            1, min(max_exams_per_student, n_exams) + 1
        )

        exams = rng.choice(
            n_exams,
            size=count,
            replace=False
        ).astype(np.int32)

        students.append(exams)

    name = f"synthetic_{n_exams}e_{n_students}s"

    return instance_from_students(
        students,
        n_exams,
        n_slots,
        name,
    )


if __name__ == "__main__":
    inst = generate_instance()

    print("Instance:", inst.name)
    print("Number of exams:", inst.n_exams)
    print("Number of students:", inst.n_students)
    print("Number of slots:", inst.n_slots)
    print("Conflict graph arrays:")
    print("ptr:", inst.ptr.dtype, inst.ptr.shape)
    print("nbr:", inst.nbr.dtype, inst.nbr.shape)
    print("wt:", inst.wt.dtype, inst.wt.shape)
