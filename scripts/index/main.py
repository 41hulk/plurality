"""
Convert CSV from Google Spreadsheet into more useful format
"""

import os
import re
from collections import defaultdict
import json
import csv

PLURALITY = "\u2ffb"

# Make section pages mapping

SECTION_PAGES_MAPPINGS_str = """
1-1 1
2-0 6
2-0 3
2-1 47
2-2 64
3-0 88
3-1 94
3-2 112
3-3 132
4-0 162
4-1 180
4-2 209
4-3 231
4-4 253
4-5 279
5-0 287
5-1 307
5-2 319
5-3 334
5-4 347
5-5 365
5-6 379
5-7 392
6-0 413
6-1 429
6-2 446
6-3 464
6-4 475
7-0 481
7-1 512
"""
lines = SECTION_PAGES_MAPPINGS_str.strip().splitlines()
items = [line.split() for line in lines]
SECTION_START = {}
for section, page in items:
    SECTION_START[section] = int(page)
SECTION_END = {}
for i in range(len(lines) - 1):
    SECTION_END[items[i][0]] = int(items[i + 1][1])
SECTION_END["7-1"] = 522  # last page


def normalize_section_name(s):
    "XX-YY -> X-Y"
    return "-".join(str(x) for x in [int(x) for x in s.split("-")])


def remove_palen(s):
    "`AAA (BBB)` -> `AAA`"
    return k.split("(")[0].strip()


CSV_FILE = "Plurality Book Indexing Exercise - Candidates.csv"
# This will get the absolute path of the current script file.
script_directory = os.path.dirname(os.path.abspath(__file__))

# keywords which should avoid mechine search, such as `X`(Twitter) or `her`(Movie name)
ignore_file = os.path.join(script_directory, "ignore.txt")
IGNORE = open(ignore_file).read().strip().splitlines()
# TODO: need to pick page-number by hand because it is not searched automatically

# keywords which should case sensitive and word boundary sensitive, such as `BERT`, `ROC`, `UN`
ignore_file = os.path.join(script_directory, "case_sensitive.txt")
CASE_SENSITIVE = open(ignore_file).read().strip().splitlines()

# List the contents of the target directory.
_pages = json.load(open(os.path.join(script_directory, "book.json")))
pages = {}
pages_lower = {}
for _p in _pages:
    p = int(_p) - 10  # page numbered 1 is page 11 on PDF
    pages[p] = _pages[_p]
    pages_lower[p] = _pages[_p].lower()


lines = open(os.path.join(script_directory, CSV_FILE)).readlines()[1:]
keywords = set()
keyword_recorded_by_human = defaultdict(set)
for row in csv.reader(lines):
    k = row[1]
    keywords.add(k)
    keyword_recorded_by_human[k].add(normalize_section_name(row[2]))


# find keyword occurence in other sections
keyword_occurence = defaultdict(list)
section_occurence = defaultdict(int)
for k in keywords:
    # find occurence in other sections
    if k in IGNORE:
        continue

    mask = [0] * len(pages)
    for section in keyword_recorded_by_human[k]:
        for p in range(SECTION_START[section], SECTION_END[section]):
            mask[p] = 1

    for p in pages:
        if not mask[p]:
            continue
        if k in CASE_SENSITIVE:
            if k in pages[p]:
                keyword_occurence[k].append(p)
                section_occurence[p] += 1
        else:
            if k.lower() in pages_lower[p]:
                keyword_occurence[k].append(p)
                section_occurence[p] += 1
                continue
            if "(" in k:
                # if keywords looks `AAA (BBB)` style, use occurrence of `AAA` instead
                k2 = remove_palen(k)
                if not k2 or k2 in IGNORE:
                    continue
                if k2.lower() in pages[p]:
                    keyword_occurence[k].append(p)
                    section_occurence[p] += 1
                    continue

with open(os.path.join(script_directory, "no_occurence.txt"), "w") as warn_no_occurence:
    print("Keywords\tSections", file=warn_no_occurence)
    for k in sorted(keywords):
        if not keyword_occurence[k] and k not in IGNORE:
            sections = ", ".join(sorted(keyword_recorded_by_human[k]))
            print(f"{k}\t{sections}", file=warn_no_occurence)


too_many_occurrence = []
with open(os.path.join(script_directory, "keyword_occurrence.tsv"), "w") as f:
    print(f"Keywords\tPages", file=f)

    for k in sorted(keyword_occurence, key=lambda x: (x.lower(), x)):
        occ = []
        prev = -999
        for p in sorted(keyword_occurence[k]):
            if p != prev + 1:  # ignore continuous pages
                occ.append(p)
            prev = p
        occ_str = ", ".join(str(p) for p in occ)
        k = k.replace('"', "")  # care mulformed TSV such as `Diversity of "groups"`
        print(f"{k}\t{occ_str}", file=f)

        if len(occ) >= 5:
            human = ", ".join(sorted(keyword_recorded_by_human[k]))
            k = k.replace('"', "")  # care mulformed TSV such as `Diversity of "groups"`
            too_many_occurrence.append((len(keyword_occurence[k]), k, human, occ_str))


too_many_occurrence.sort(reverse=True)
with open(os.path.join(script_directory, "too_many_occurrence.tsv"), "w") as f:
    print(f"Keywords\tSection(by Human)\tSection(by Script)", file=f)
    for num, k, human, occ in too_many_occurrence:
        print(f"{k}\t{human}\t{occ}", file=f)
