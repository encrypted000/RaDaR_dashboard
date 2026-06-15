from lib.biopsy_backend import run_backend as run_biopsy
from lib.genetics_backend import run_backend as run_genetics
from lib.home_backend import run_backend as run_home
from lib.diagnoses_backend import run_backend as run_diagnoses
from lib.children_backend import run_backend as run_children


def run_all():
    print("===================================")
    print("Running ALL backends...")
    print("===================================")

    print("\n--- Running Biopsy Backend ---")
    run_biopsy()

    print("\n--- Running Genetics Backend ---")
    run_genetics()

    print("\n--- Running Home Backend ---")
    run_home()

    print("\n--- Running Diagnoses Backend ---")
    run_diagnoses()

    print("\n--- Running Children Backend ---")
    run_children()

    print("\n===================================")
    print("All backends completed successfully.")
    print("===================================")


if __name__ == "__main__":
    run_all()
