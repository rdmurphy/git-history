# git-history

[![PyPI](https://img.shields.io/pypi/v/git-history.svg)](https://pypi.org/project/git-history/)
[![Changelog](https://img.shields.io/github/v/release/simonw/git-history?include_prereleases&label=changelog)](https://github.com/simonw/git-history/releases)
[![Tests](https://github.com/simonw/git-history/workflows/Test/badge.svg)](https://github.com/simonw/git-history/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/git-history/blob/master/LICENSE)

Tools for analyzing Git history using SQLite

## Installation

Install this tool using `pip`:

    $ pip install git-history

## Usage

This tool can be run against a Git repository that holds a file that contains JSON, CSV/TSV or some other format and which has multiple versions tracked in the Git history. See [Git scraping](https://simonwillison.net/2020/Oct/9/git-scraping/) to understand how you might create such a repository.

The `file` command analyzes the history of an individual file within the repository, and generates a SQLite database table that represents the different versions of that file over time.

The file is assumed to contain multiple objects - for example, the results of scraping an electricity outage map or a CSV file full of records.

Assuming you have a file called `incidents.json` that is a JSON array of objects, with multiple versions of that file recorded in a repository.

Change directory into the GitHub repository in question and run the following:

    git-history file incidents.db incidents.json

This will create a new SQLite database in the `incidents.db` file with two tables:

- `commits` containing a row for every commit, with a `hash` column and the `commit_at` date.
- `items` containing a row for every item in every version of the `filename.json` file - with an extra `_commit` column that is a foreign key back to the `commits` table.

If you have 10 historic versions of the `incidents.json` file and each one contains 30 incidents, you will end up with 10 * 30 = 300 rows in your `items` table.

### De-duplicating items using IDs

If your objects have a unique identifier - or multiple columns that together form a unique identifier - you can use the `--id` option to de-duplicate and track changes to each of those items over time.

If there is a unique identifier column called `IncidentID` you could run the following:

    git-history file incidents.db incidents.json --id IncidentID

This will create three tables - `commits`, `items` and `item_versions`.

The `items` table will contain just the most recent version of each row, de-duplicated by ID.

The `item_versions` table will contain a row for each captured differing version of that item, plus the following columns:

- `_item` as a foreign key to the `items` table
- `_commit` as a foreign key to the `commits` table
- `_version` as the numeric version number, starting at 1 and incrementing for each captured version

If you have already imported history, the command will skip any commits that it has seen already and just process new ones. This means that even though an initial import could be slow subsequent imports should run a lot faster.

Additional options:

- `--repo DIRECTORY` - the path to the Git repository, if it is not the current working directory.
- `--branch TEXT` - the Git branch to analyze - defaults to `main`.
- `--id TEXT` - as described above: pass one or more columns that uniquely identify a record, so that changes to that record can be calculated over time.
- `--ignore TEXT` - one or more columns to ignore - they will not be included in the resulting database.
- `--csv` - treat the data is CSV or TSV rather than JSON, and attempt to guess the correct dialect
- `--convert TEXT` - custom Python code for a conversion, see below.
- `--import TEXT` - Python modules to import for `--convert`.
- `--ignore-duplicate-ids` - if a single version of a file has the same ID in it more than once, the tool will exit with an error. Use this option to ignore this and instead pick just the first of the two duplicates.
- `--silent` - don't show the progress bar.

Note that `_id`, `_item`, `_version`, `_commit` and `rowid` are considered column names for the purposes of this tool. If your data contains any of these they will be renamed to `_id_`, `_item_`, `_version_`, `_commit_` or `_rowid_` to avoid clashing with the reserved columns.

If you have a column with a name such as `_commit_` it will be renamed too, adding an additional trailing underscore, so `_commit_` becomes `_commit__` and `_commit__` becomes `_commit__`.

### CSV and TSV data

If the data in your repository is a CSV or TSV file you can process it by adding the `--csv` option. This will attempt to detect which delimiter is used by the file, so the same option works for both comma- and tab-separated values.

    git-history file trees.db trees.csv --id TreeID

### Custom conversions using --convert

If your data is not already either CSV/TSV or a flat JSON array, you can reshape it using the `--convert` option.

The format needed by this tool is an array of dictionaries that looks like this:

```json
[
    {
        "id": "552",
        "name": "Hawthorne Fire",
        "engines": 3
    },
    {
        "id": "556",
        "name": "Merlin Fire",
        "engines": 1
    }
]
```

If your data does not fit this shape, you can provide a snippet of Python code to converts the on-disk content of each stored file into a Python list of dictionaries.

For example, if your stored files each look like this:

```json
{
    "incidents": [
        {
            "id": "552",
            "name": "Hawthorne Fire",
            "engines": 3
        },
        {
            "id": "556",
            "name": "Merlin Fire",
            "engines": 1
        }
    ]
}
```
You could use the following Python snippet to convert them to the required format:

```python
json.loads(content)["incidents"]
```
(The `json` module is exposed to your custom function by default.)

You would then run the tool like this:

    git-history file database.db incidents.json \
      --id id \
      --convert 'json.loads(content)["incidents"]'

The `content` variable is always a `bytes` object representing the content of the file at a specific moment in the repository's history.

You can import additional modules using `--import`. This example shows how you could read a CSV file that uses `;` as the delimiter:

    git-history file trees.db ../sf-tree-history/Street_Tree_List.csv \
      --repo ../sf-tree-history \
      --import csv \
      --import io \
      --convert '
        fp = io.StringIO(content.decode("utf-8"))
        return list(csv.DictReader(fp, delimiter=";"))
        ' \
      --id TreeID

If your Python code spans more than one line it needs to include a `return` statement.

You can also use Python generators in your `--convert` code, for example:

    git-history file stats.db package-stats/stats.json \
        --repo package-stats \
        --convert '
        data = json.loads(content)
        for key, counts in data.items():
            for date, count in counts.items():
                yield {
                    "package": key,
                    "date": date,
                    "count": count
                }
        ' --id package --id date

This conversion function expects data that looks like this:

```json
{
    "airtable-export": {
        "2021-05-18": 66,
        "2021-05-19": 60,
        "2021-05-20": 87
    }
}
```

## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:

    cd git-history
    python -m venv venv
    source venv/bin/activate

Or if you are using `pipenv`:

    pipenv shell

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
