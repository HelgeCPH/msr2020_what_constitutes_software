"""
Run me like:
$ python analyze.py 3 > out/results.log 2>&1

The number provides the amount of used cores. mp.cpu_count() is the default
"""


import os
import sys
import time
import shutil
import socket
import logging
import traceback
import pandas as pd
import multiprocessing as mp
from glob import glob
from zipfile import ZipFile
from zipfile import BadZipFile
from main import get_info_from_droid, get_info_from_file_magic_many


logging.basicConfig(
    format="%(asctime)s %(message)s", stream=sys.stdout, level=logging.INFO
)
logging.info(f"Running as process no.: {os.getpid()}")

if socket.gethostname() == "experiment":
    # It is running on the remote server
    MAIN_DIR = os.getcwd()
else:
    # It is running on the local machine with this directory structure
    MAIN_DIR = os.path.dirname(os.getcwd())
CSV_DIR = os.path.join(MAIN_DIR, "out")
REPO_DIR = os.path.join(CSV_DIR, "repos")
RESULTS_DIR = os.path.join(CSV_DIR, "results")
WORKING_DIR = os.path.join(CSV_DIR, "intermediate")


def create_repo_name_lookup_table():
    csv_files = glob(os.path.join(CSV_DIR, "repos*.csv"))
    # Make one DataFrame out of all these csv files
    df_repos = pd.concat((pd.read_csv(f) for f in csv_files), ignore_index=True)

    repo_name_loopup = {
        n.replace("/", "_"): n for n in df_repos.full_name.unique()
    }

    return repo_name_loopup


REPO_NAME_LOOPUP = create_repo_name_lookup_table()


def unzip_archive(zip_path):
    out_dir = zip_path.replace(".zip", "")
    try:
        if not os.path.isdir(out_dir):
            with ZipFile(zip_path, "r") as zip_ref:
                # Put the ectracted archive next to the zip files
                # TODO: Think about if it should go somewhere else...
                zip_ref.extractall(out_dir)

        return out_dir
    except BadZipFile:
        logging.error(f"{zip_path} does not seem to be a valid ZIP file.")
    except Exception as e:
        traceback.print_exc()
        return ""


def unzip_all_parallel(zip_files, processes=1):
    start_wall_time = time.time()
    # Speed up uncompression with multiprocessing:
    # unzipped_dirs = [unzip_archive(z) for z in zip_files]
    with mp.Pool(processes=processes) as pool:
        unzipped_dirs = pool.map(unzip_archive, zip_files)

    end_wall_time = time.time()
    wall_time = (end_wall_time - start_wall_time) / 60  # in minutes now
    no_files = len(zip_files)
    logging.info(f"Unzipping {no_files} took {wall_time}")
    return unzipped_dirs


def analyze(zip_file):
    out_csv_short = os.path.basename(zip_file).replace(".zip", ".csv")
    out_csv = os.path.join(RESULTS_DIR, out_csv_short)

    # run the analysis only if it has not been done yet
    if not os.path.isfile(out_csv):
        logging.info(f"Starting analyzis of {zip_file}")
        # unpack the zip archive
        dir_to_analyze = unzip_archive(zip_file)
        if dir_to_analyze:
            # Analyse it with file magic
            magic_df = get_info_from_file_magic_many(
                dir_to_analyze, path_for_stats=WORKING_DIR
            )
            # Analyse it with droid
            # I do not think that I can have parallel instances of droid
            # running... I tried it by hand on the CLI, so I think I can use
            # multiprocessing anyways
            if os.path.basename(zip_file) != "danielmiessler_SecLists.zip":
                # This is a hack! The repo contains zip bombs and droid cannot handle that!
                # I hope it is the only repo like that...
                droid_df = get_info_from_droid(
                    dir_to_analyze, path_for_stats=WORKING_DIR
                )
                # Analyse it with linguist
                # ... -> Do that in a third step

                # join the dataframes on filenames
                magic_df = magic_df.set_index("path")
                droid_df = droid_df.set_index("FILE_PATH")

                repo_df = magic_df.join(droid_df)
            else:
                magic_df = magic_df.set_index("path")
                repo_df = magic_df

            repo_df["owner"] = REPO_NAME_LOOPUP[
                os.path.splitext(out_csv_short)[0]
            ]
            repo_df.to_csv(out_csv)

            logging.info(f"-> Created {out_csv_short}")
            logging.info(f"Done analyzing {zip_file}")
            try:
                # remove the analyzed directory to save disk space
                shutil.rmtree(dir_to_analyze)
            except:
                msg = f"Could not remove {dir_to_analyze} after analyzis."
                logging.error(msg)
        else:
            # Then there went something wrong unzipping the archive...
            msg = (
                f"Skipped analyzing {dir_to_analyze}"
                + " as I could not unzip the archive."
            )
            logging.error(msg)
    else:
        logging.info(
            f"Skipped analyzis of {zip_file}. Already done in {out_csv}"
        )

    return out_csv


def analyze_all_parallel(zips_to_analyze, processes=1):
    start_wall_time = time.time()

    with mp.Pool(processes=processes) as pool:
        created_csvs = pool.map(analyze, zips_to_analyze)

    end_wall_time = time.time()
    wall_time = (end_wall_time - start_wall_time) / 60  # in minutes now
    no_files = len(created_csvs)
    msg = (
        f"Analyzis of {no_files} repos with {processes} parallel processes"
        + f" took {wall_time:.2f} minutes"
    )
    logging.info(msg)
    return created_csvs


if __name__ == "__main__":

    csv_files = glob(os.path.join(CSV_DIR, "repo*.csv"))

    # Make one DataFrame out of all these csv files
    df = pd.concat((pd.read_csv(f) for f in csv_files), ignore_index=True)

    zip_files = [fn.replace("/", "_") + ".zip" for fn in df.full_name]
    zip_files = [os.path.join(REPO_DIR, z) for z in zip_files]
    df["zips"] = zip_files

    # Filter zip files for those that were already processed
    zip_files = [
        z
        for z in zip_files
        if not os.path.isfile(
            os.path.join(
                RESULTS_DIR, os.path.basename(z).replace(".zip", ".csv")
            )
        )
    ]

    if len(sys.argv) > 1:
        processes = int(sys.argv[1])
    else:
        processes = mp.cpu_count()

    # Creates the CSV files
    created_csvs = analyze_all_parallel(zip_files, processes=processes)
