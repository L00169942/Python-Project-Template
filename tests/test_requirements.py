# Copyright (C) 2021 Intel Corporation
# SPDX-License-Identifier: GPL-3.0-or-later

import csv
import json
import re
import subprocess
import tempfile
from importlib.metadata import version
from pathlib import Path

ROOT_PATH = Path(__file__).parent.parent
TEMP_DIR = Path(tempfile.mkdtemp(prefix="requirements_scan-"))

REQ_TXT = str(ROOT_PATH / "requirements.txt")
TRIAGE_JSON = str(ROOT_PATH / "triage.json")
OUTPUT_JSON = str(TEMP_DIR / "output.json")  # the output is a temp file
DOC_TXT = str(ROOT_PATH / "doc" / "requirements.txt")

SCAN_CSV = str(ROOT_PATH / "cve_bin_tool_requirements.csv")

HTML_DEP_PATH_PATHLIB = (
    ROOT_PATH / "cve_bin_tool" / "output_engine" / "html_reports" / "js"
)
HTML_DEP_PATH = str(HTML_DEP_PATH_PATHLIB)

HTML_DEP_CSV = str(HTML_DEP_PATH_PATHLIB / "dependencies.csv")

# Dependencies that currently have CVEs
# Remove from the list once they are updated
ALLOWED_PACKAGES = ["reportlab"]


def get_out_of_sync_packages(csv_name, txt_name):

    new_packages = set()
    removed_packages = set()
    csv_package_names = set()
    txt_package_names = set()

    with open(csv_name) as csv_file, open(txt_name) as txt_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader)
        for (_, product) in csv_reader:
            csv_package_names.add(product)
        lines = txt_file.readlines()
        for line in lines:
            txt_package_names.add(re.split(">|\\[|;|=|\n", line)[0])
        new_packages = txt_package_names - csv_package_names
        removed_packages = csv_package_names - txt_package_names

    return (new_packages, removed_packages)





def get_cache_csv_data(file):

    data = []

    with open(file) as f:
        r = csv.reader(f)
        next(r)
        for (vendor, product) in r:
            if file is HTML_DEP_CSV:
                file_name = f"{HTML_DEP_PATH}/{product}"
                if not file_name.endswith(".js"):
                    file_name += ".js"
                with open(file_name) as f:
                    file_content = f.read()
                    html_dep_version = re.search(
                        r"v([0-9]+\.[0-9]+\.[0-9]+)", file_content
                    ).group(1)
                    if product not in ALLOWED_PACKAGES:
                        data.append((vendor, product, html_dep_version))
            else:
                if "_not_in_db" not in vendor and product not in ALLOWED_PACKAGES:
                    data.append((vendor, product, version(product)))

        return data


# Test to check for CVEs in cve-bin-tool requirements/dependencies
def test_requirements():

    cache_csv_data = (
        get_cache_csv_data(HTML_DEP_CSV)
    )

    # writes a cache CSV file
    with open(SCAN_CSV, "w") as f:
        writer = csv.writer(f)
        fieldnames = ["vendor", "product", "version"]
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for row in cache_csv_data:
            writer.writerow(row)

    # Disabled check, see below
    # cve_check = subprocess.run(
    subprocess.run(
        [
            "python",
            "-m",
            "cve_bin_tool.cli",
            "--input-file",
            SCAN_CSV,
            "--merge",
            TRIAGE_JSON,
            "--format",
            "json",
            "--output-file",
            OUTPUT_JSON,
        ]
    )
    # Open the JSON output and check for any issues that are not Mitigated or Ignored
    # We should still fail on NewFound, Unexplored or Confirmed CVEs.
    with open(OUTPUT_JSON) as f:
        output_json = json.load(f)
        for entry in output_json:
            assert entry["remarks"] in ["Mitigated", "Ignored"]

    # Disabled until we fix how ignored/mitigated issues are listed
    # See https://github.com/intel/cve-bin-tool/issues/1752
    # assert (
    #    cve_check.returncode == 0
    # ), f"{cve_check.returncode} dependencies/requirements have CVEs"
