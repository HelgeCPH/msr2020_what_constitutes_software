"""
Run me like:

$ python download_gh_repos.py > out/download.log 2>&1
"""

import os
import git  # Installed it via: `conda install GitPython`
import sys
import shutil
import socket
import requests
import subprocess
import pandas as pd
from glob import glob
from time import sleep
from collect_gh_repos import LANGUAGES
import logging


DOWNLOAD = ("ZIP", "CLONE")
DOWNLOAD_TYPE = DOWNLOAD[0]
logging.basicConfig(
    format="%(asctime)s %(message)s", stream=sys.stdout, level=logging.INFO
)


def wget(url, outname):
    with requests.get(url, stream=True) as req:
        with open(outname, "wb") as fp:
            shutil.copyfileobj(req.raw, fp)

    size_of_zip = os.path.getsize(outname) / 1024 ** 2  # Convert to MB
    return outname, size_of_zip


def download_repo(row, download_type="ZIP"):
    if download_type == "ZIP":
        zip_file = row.full_name.replace("/", "_") + ".zip"
        out_file = os.path.join("out", "repos", zip_file)
        if not os.path.isfile(out_file):
            outname, size_of_zip = wget(row.zip_url, out_file)
            # I hope this break is long enough...
            sleep(0.5)
        else:
            outname = out_file
            # We do not want to add its size up multiple times later
            size_of_zip = 0
        return outname, size_of_zip
        # cmd = ["unzip", zip_file]
        # subprocess.run(cmd)

    elif download_type == "CLONE":
        out_dir = row.full_name.replace("/", "_")
        out_dir = os.path.join("out", "repos", out_dir)
        if not os.path.isdir(out_dir):
            repo = git.Repo.clone_from(row.git_url, out_dir, branch="master")
            # I hope this break is long enough...
            sleep(0.5)
        return out_dir, _compute_dir_size(out_dir)


def _compute_unzipped_size(fname):
    cmd = f"unzip -l {fname} | tail -1"
    p = subprocess.check_output(cmd, shell=True)
    try:
        # convert it to mega bytes
        real_size = int(p.decode("utf-8").split()[0]) / 1024 ** 2
    except ValueError:
        # In rare cases, the zip file seems to be corrupt, then I just return
        # the size of the zipped file, as the uncompressed version is at least
        # as big as this

        # Search for: `unzip:  cannot find zipfile directory in one`
        logging.error(f"Cannot determine size of zipped {fname}...")
        real_size = os.path.getsize(fname) / 1024 ** 2
    return real_size


def _compute_dir_size(directory):
    cmd = f"du -sk {directory}"
    p = subprocess.check_output(cmd, shell=True)
    # convert it to mega bytes
    real_size = int(p.decode("utf-8").split()[0]) / 1024
    return real_size


if __name__ == "__main__":
    if socket.gethostname() == "experiment":
        # It is running on the remote server
        main_dir = os.getcwd()
    else:
        # It is running on the loca machine with this directory structure
        main_dir = os.path.dirname(os.getcwd())
    csv_dir = os.path.join(main_dir, "out")
    repo_dir = os.path.join(csv_dir, "repos")

    csv_files = glob(os.path.join(csv_dir, "repos*.csv"))
    # Make one DataFrame out of all these csv files
    df = pd.concat((pd.read_csv(f) for f in csv_files), ignore_index=True)

    # Download the repos as ZIP files for now
    total_size = 0.0
    total_real_size = 0.0
    idx = 0
    for idx, row in df.iterrows():
        outfile, size = download_repo(row, download_type=DOWNLOAD_TYPE)
        outfile_short = os.path.basename(outfile)

        total_size += size
        if DOWNLOAD_TYPE == "ZIP":
            # compute the unpacked size
            real_size = _compute_unzipped_size(outfile)
            total_real_size += real_size

            msg = f"Downloaded: {outfile_short}. On disk {total_size:.2f}MB - "
            msg += f"unzipped {total_real_size:.2f}MB..."
            logging.info(msg)
        else:
            msg = f"Downloaded: {outfile_short}. On disk {total_size:.2f}MB - "
            logging.info(msg)
