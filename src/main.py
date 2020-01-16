import os
import sys
import yaml

# Depends on:
# brew install libmagic
# pip install filemagic
import magic
import logging
import subprocess
import numpy as np
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from magic.api import MagicError
from purpose import get_purpose_df


COLUMNS_FOR_MAGIC = ["path", "kind", "mime_type", "encoding", "ext"]


def lang_yaml_to_df(fname="languages.yml"):
    """
    Do it once for easy lookup
    """
    with open(fname) as fp:
        contents = fp.read()
    yml = yaml.load(contents, Loader=yaml.FullLoader)

    languages = yml.keys()
    values = []
    for l, entry in zip(languages, yml.values()):
        lang_type = entry["type"]
        try:
            aliases = entry["aliases"]
        except KeyError:
            aliases = ""
        try:
            group = entry["group"]
        except KeyError:
            group = ""
        try:
            fnames = entry["filenames"]
        except KeyError:
            fnames = ""
        try:
            extensions = entry["extensions"]
        except KeyError:
            extensions = ""
        try:
            interpreters = entry["interpreters"]
        except KeyError:
            interpreters = ""
        try:
            mime_type = entry["codemirror_mime_type"]
        except KeyError:
            mime_type = ""
        row = (
            l,
            lang_type,
            aliases,
            group,
            fnames,
            extensions,
            interpreters,
            mime_type,
        )
        values.append(row)

    columns = [
        "language",
        "type",
        "aliases",
        "group",
        "filenames",
        "extensions",
        "interpreters",
        "mime_type",
    ]
    df = pd.DataFrame(values, columns=columns)
    df = df.replace("", np.NaN)
    return df


def find_all_files(base_path):
    globbed = list(Path(base_path).glob("**/*"))
    all_files = [f for f in globbed if f.is_file() and not f.is_symlink()]
    all_files_wo_git = [f for f in all_files if not ".git" in f.parts]
    return all_files_wo_git


def get_info_from_file_magic_many(repo_dir, path_for_stats="/tmp"):
    all_files = find_all_files(repo_dir)
    rows = [get_info_from_file_magic(f) for f in tqdm(all_files)]
    df = pd.DataFrame(rows, columns=COLUMNS_FOR_MAGIC)

    repo_name = os.path.basename(repo_dir)
    stats_csv = os.path.join(path_for_stats, f"magic_{repo_name}.csv")
    df.to_csv(stats_csv)
    return df


def get_info_from_file_magic(fname):
    # Get what the `file` tool would say about it
    try:
        with magic.Magic() as m:
            f_kind = m.id_filename(os.fspath(fname))
        flags = magic.MAGIC_MIME_TYPE | magic.MAGIC_MIME_ENCODING
        with magic.Magic(flags=flags) as m:
            f_mime_type, f_encoding = m.id_filename(os.fspath(fname)).split(
                "; "
            )
        extension = fname.suffix
        if not extension:
            extension = np.nan
        return (
            os.path.abspath(os.fspath(fname)),
            f_kind,
            f_mime_type,
            f_encoding,
            extension,
        )
    except UnicodeDecodeError:
        msg = f"Skipped analysis of {fname.parts} due to unicode decoding issue"
        logging.warning(msg)
        return (np.nan, np.nan, np.nan, np.nan, np.nan)
    except ValueError:
        msg = f"Skipped analysis of {fname.parts} due to mime type split issue"
        logging.warning(msg)
        return (np.nan, np.nan, np.nan, np.nan, np.nan)
    except MagicError:
        msg = f"Skipped analysis of {fname.parts} due to magic issue"
        logging.warning(msg)
        return (np.nan, np.nan, np.nan, np.nan, np.nan)


def get_info_from_linguist_db_many(repo_dir):
    df = lang_yaml_to_df()
    df_filename_view = df[pd.notna(df.filenames)]
    df_extensions_view = df[pd.notna(df.extensions)]


def get_info_from_linguist_db(fname):
    pass


def get_info_from_droid(repo_dir, path_for_stats="/tmp"):
    """
    It is easiest for Droid to analyse an entire directory.
    Droid comes from here: http://digital-preservation.github.io/droid/
    I set it up by:

    ```bash
    $ cd ~/Documents/workspace/Java
    $ git clone https://github.com/digital-preservation/droid.git
    $ cd droid
    $ mvn install
    $ cp droid-binary/target/droid-binary-6.5-SNAPSHOT-bin.zip ~/bin/droid
    $ cd ~/bin/droid
    $ unzip droid-binary-6.5-SNAPSHOT-bin.zip
    ```

    The following is based on https://github.com/CarletonArchives/DROID-Batch-Processor/blob/master/DroidRunner.py
    droid does not want to have
    one has to first create a profile...

    Call this function for example like:
    repo_dir = "..."
    get_info_from_droid(repo_dir, path_for_stats="/tmp")
    """
    repo_name = os.path.basename(repo_dir)

    binary = "droid/droid.sh"
    binary = os.path.join(os.getenv("HOME"), binary)
    profile_file = os.path.join(path_for_stats, f"droid_{repo_name}.droid")
    cmd_create_profile_args = [
        "-q",
        "-R",
        "-a",
        f'"{repo_dir}"',
        "-p",
        f'"{profile_file}"',
    ]
    cmd_create_profile = [binary] + cmd_create_profile_args

    stats_csv = os.path.join(path_for_stats, f"droid_{repo_name}.csv")
    cmd_create_stats_args = [
        "-q",
        "-p",
        f'"{profile_file}"',
        "-e",
        f'"{stats_csv}"',
    ]
    cmd_create_stats = [binary] + cmd_create_stats_args

    try:
        print("Running " + " ".join(cmd_create_profile))
        p = subprocess.run(cmd_create_profile)
        print("Running " + " ".join(cmd_create_stats))
        p = subprocess.run(cmd_create_stats)
        os.remove("./derby.log")
    except:
        # TODO: what to do here log, interupt???
        pass

    def git_metadata(path):
        # This is not elegant and works only on Unixish file systems
        return "/.git/" in path

    columns_to_keep = [
        "FILE_PATH",
        "NAME",
        "TYPE",
        "EXT",
        "EXTENSION_MISMATCH",
        "PUID",
        "MIME_TYPE",
    ]
    if os.path.isfile(stats_csv):
        try:
            df = pd.read_csv(stats_csv)
        except:
            logging.warning(f"Skipped line(s) from {stats_csv}, check it!")
            df = pd.read_csv(stats_csv, error_bad_lines=False)

        # Filter the DataFrame for only those parts that we need later...
        df_small = df[columns_to_keep]
        # We are only interested in files...
        df_small = df_small[df_small.TYPE == "File"]
        # Droid looks into ZIP and other archives, we would like to only take
        # files that are proper files, i.e., the ZIP archive itself
        df_small = df_small[pd.notna(df_small.FILE_PATH)]
        # Remove all files
        mask = [not git_metadata(p) for p in df_small.FILE_PATH]
        df_small = df_small[mask]
        return df_small
    else:
        # Just return an empty dataframe
        return pd.DataFrame([], columns=columns_to_keep)
