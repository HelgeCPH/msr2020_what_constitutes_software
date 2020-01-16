#!/usr/bin/env python3
"""
Run me like:

./collect_gh_repos.py repos.csv skipped_from_collection.log
"""
import yaml
import pandas as pd
import os
import csv
import sys
import requests
from datetime import datetime

from time import sleep
from github import Github


LANGUAGES = [
    "abap",
    "ada",
    "asm",
    "c",
    "cobol",
    "cpp",
    "csharp",
    "d",
    "erlang",
    "fortran",
    "fsharp",
    "go",
    "groovy",
    "java",
    "javascript",
    "kotlin",
    "lua",
    "objectivec",
    "ocaml",
    "perl",
    "php",
    "python",
    "ruby",
    "scala",
    "swift",
]


g = Github(login_or_token=os.getenv("GITHUB_API_KEY"))


def collect_repo_info(lang, outpath="out"):
    # Finds all public repos by stars in descenging order
    if lang:
        query = "language:" + lang
    else:
        query = "is:public"
    repositories = g.search_repositories(
        query=query, sort="stars", order="desc"
    )
    amount = repositories.totalCount
    print(f"There are {str(amount)} repos for {lang}...")

    outfile = os.path.join(outpath, f"repos_{lang}.csv")
    with open(outfile, "w") as fp:
        csvwriter = csv.writer(fp)
        csvwriter.writerow(
            [
                "watchers",
                "language",
                "git_url",
                "html_url",
                "zip_url",
                "full_name",
                "size",
            ]
        )

        for idx, repo in enumerate(repositories):
            repo_zip = repo.get_archive_link(archive_format="zipball")
            csvwriter.writerow(
                [
                    repo.watchers,
                    repo.language,
                    repo.git_url,
                    repo.html_url,
                    repo_zip,
                    repo.full_name,
                    repo.size,
                ]
            )

            rate_left, _ = g.rate_limiting
            if rate_left == 0:
                ts = g.rate_limiting_resettime
                reset_time = datetime.utcfromtimestamp(ts)

                now = datetime.now()
                if now < reset_time:
                    time_to_wait = reset_time - now
                    print(f"Sleeping for {str(time_to_wait)}")
                    sleep(time_to_wait)

            # To prevent:
            # RateLimitExceededException: 403 {'documentation_url':
            # 'https://developer.github.com/v3/#abuse-rate-limits',
            # 'message': 'You have triggered an abuse detection mechanism.
            # Please wait a few minutes before you try again.'}
            sleep(0.5)


if __name__ == "__main__":
    if socket.gethostname() == "experiment":
        # It is running on the remote server
        outpath = os.path.join(os.getcwd(), "out")
    else:
        # It is running on the loca machine with this directory structure
        main_dir = os.path.join(os.path.dirname(os.getcwd()), "out")
    for lang in LANGUAGES:
        collect_repo_info(lang)
        sleep(10)
