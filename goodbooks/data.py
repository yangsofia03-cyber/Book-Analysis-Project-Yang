"""Download, load, clean and save the goodbooks-10k dataset."""

import os # working with files and folders (building paths, checking of a file exists)

import numpy as np
import pandas as pd
import requests

from goodbooks.analysis import weighted_rating
from goodbooks.genres import NO_GENRE, assign_genres

# The root of the project is the parent of the folder of this module
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

BASE_URL = "https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/"
FILE_NAMES = ["books", "ratings", "tags", "book_tags"]
TIMEOUT_SECONDS = 60

# ratings.csv has 6 million rows: small integer types bring it
# from about 140 MB to 40 MB in memory
DTYPES = {
    "ratings": {"user_id": "int32", "book_id": "int16", "rating": "int8"},
}

STAR_COLUMNS = ["ratings_1", "ratings_2", "ratings_3", "ratings_4", "ratings_5"]
BOOK_COLUMNS = [
    "book_id",
    "goodreads_book_id",
    "authors",
    "original_publication_year",
    "title",
    "language_code",
    "average_rating",
    "ratings_count",
    "image_url", 
] + STAR_COLUMNS

# A series at the end of a title, e.g. "The Hunger Games (The Hunger Games, #1)"
SERIES_PATTERN = r"\s*\([^()]*#[^()]*\)$"
# Box sets and collections are not new works of an author
COMPILATION_PATTERN = r"(?i)box ?set|boxed set|collection|omnibus|\bcomplete\b"

# Publication eras: each bin includes its left edge (right=False)
ERA_BINS = [-10_000, 1900, 1950, 2000, 2010, 2018]
ERA_LABELS = ["Before 1900", "1900-1949", "1950-1999", "2000-2009", "2010-2017"]


def download_file(url, path):
    """Download a file from the web, unless it is already on disk."""
    if os.path.exists(path):
        return
    response = requests.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(response.content)


def download_dataset(data_dir=DATA_DIR):
    """
    Download the CSV files of goodbooks-10k into data_dir (only the missing ones).

    Raises
    ------
    requests.exceptions.RequestException
        If a file can't be downloaded (no connection, wrong URL, ...).
    """
    for name in FILE_NAMES:
        download_file(BASE_URL + name + ".csv", os.path.join(data_dir, name + ".csv"))


def load_csv(name, data_dir=DATA_DIR):
    """
    Load one table of the dataset.

    Parameters
    ----------
    name : str
        One of ``FILE_NAMES``, e.g. ``"books"``.
    data_dir : str, optional
        Folder with the CSV files.

    Returns
    -------
    pandas.DataFrame
        The table as it is in the file.

    Raises
    ------
    FileNotFoundError
        If the file is not in data_dir.
    ValueError
        If the file is empty or is not a valid CSV file (e.g. a download
        that was interrupted).
    """
    path = os.path.join(data_dir, name + ".csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found: run download_dataset() first")
    try:
        return pd.read_csv(path, dtype=DTYPES.get(name))
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as error:
        raise ValueError(
            f"{path} is not a valid CSV file ({error}): "
            "delete it and run download_dataset() again"
        ) from error

# how much readers disagree about each book.
def add_star_std(books):
    """
    Add the standard deviation of the 1-5 stars of each book (``star_std``).

    It measures how divisive a book is: 0 if all the readers give it the
    same rating, 2 if half give it 1 star and half 5 stars.

    Parameters
    ----------
    books : pandas.DataFrame
        Table with the columns ``ratings_1`` ... ``ratings_5``.

    Returns
    -------
    pandas.DataFrame
        A copy of books, with the new column.
    """
    counts = books[STAR_COLUMNS].to_numpy()  # shape (n_books, 5)
    stars = np.arange(1, 6)
    total = counts.sum(axis=1)
    mean = counts @ stars / total
    variance = counts @ stars**2 / total - mean**2
    return books.assign(star_std=np.sqrt(variance))

# @ --> matrix multiplication. For a row of 
# counts and a list of stars, it multiplies each pair and adds them up

# books.assign(star_std=...) returns a copy of the table with the new 
# column, leaving the original unchanged, which matches the docstring.

def clean_books(books):
    """
    Clean the books table and add the columns used in the analysis.

    Parameters
    ----------
    books : pandas.DataFrame
        The raw ``books.csv``.

    Returns
    -------
    pandas.DataFrame
        A new table, with ``year``, ``era``, ``main_author``, ``short_title``,
        ``is_compilation``, ``log_ratings_count`` and ``star_std``.
    """
    df = books[BOOK_COLUMNS].drop_duplicates(subset="book_id")
    df = df.rename(columns={"original_publication_year": "year"})
    # The years are floats (2008.0) because of the missing values:
    # "Int64" keeps them as integers, with <NA> for the missing ones
    df["year"] = df["year"].astype("Int64")
    df["era"] = pd.cut(df["year"], bins=ERA_BINS, labels=ERA_LABELS, right=False)
    df["language_code"] = df["language_code"].fillna("unknown")

    # "J.K. Rowling, Mary GrandPré" -> "J.K. Rowling"
    df["main_author"] = df["authors"].str.split(",").str[0].str.strip()
    df["short_title"] = df["title"].str.replace(SERIES_PATTERN, "", regex=True)
    df["is_compilation"] = df["title"].str.contains(COMPILATION_PATTERN)
    # The number of ratings goes from a few thousands to millions: use its log
    df["log_ratings_count"] = np.log10(df["ratings_count"])
    return add_star_std(df)

#pd.cut sorts numbers into ranges (bins) and gives each range a name.

def clean_book_tags(book_tags, tags, books):
    """
    Add the tag names to the book-tag table, with ``book_id`` as identifier.

    Parameters
    ----------
    book_tags, tags : pandas.DataFrame
        The raw ``book_tags.csv`` and ``tags.csv``.
    books : pandas.DataFrame
        The books, with ``book_id`` and ``goodreads_book_id``.

    Returns
    -------
    pandas.DataFrame
        Columns ``book_id``, ``tag_name`` and ``count``.
    """
    # A few counts are negative, which makes no sense for a number of users
    valid = book_tags[book_tags["count"] > 0]
    # book_tags uses the Goodreads identifier: switch to the one of books.csv
    merged = valid.merge(
        books[["book_id", "goodreads_book_id"]], on="goodreads_book_id"
    )
    merged = merged.merge(tags, on="tag_id")
    return merged[["book_id", "tag_name", "count"]]


def load_books(data_dir=DATA_DIR):
    """
    Load the clean books, each with its genre and weighted rating.

    Parameters
    ----------
    data_dir : str, optional
        Folder with the CSV files.

    Returns
    -------
    pandas.DataFrame
        One row per book.
    """
    books = clean_books(load_csv("books", data_dir))
    book_tags = clean_book_tags(
        load_csv("book_tags", data_dir), load_csv("tags", data_dir), books
    )
    books = books.merge(assign_genres(book_tags), on="book_id", how="left")
    books["genre"] = books["genre"].fillna(NO_GENRE)
    books["weighted_rating"] = weighted_rating(
        books["average_rating"], books["ratings_count"]
    )
    return books


def load_ratings(data_dir=DATA_DIR):
    """
    Load the 6 million ratings, without invalid values and duplicates.

    Returns
    -------
    pandas.DataFrame
        Columns ``user_id``, ``book_id`` and ``rating`` (1-5), one row per
        (user, book).
    """
    ratings = load_csv("ratings", data_dir)
    ratings = ratings[ratings["rating"].between(1, 5)]
    return ratings.drop_duplicates(subset=["user_id", "book_id"], keep="last")


def find_books(books, query, max_results=20):
    """
    Find the books whose title or author contains some text.

    Parameters
    ----------
    books : pandas.DataFrame
        One row per book, with ``title`` and ``authors``.
    query : str
        The text to look for (upper and lower case are the same).
    max_results : int, optional
        The maximum number of books returned.

    Returns
    -------
    pandas.DataFrame
        The matching books, the most rated first (all the books if query is
        empty).
    """
    query = query.strip()
    # regex=False: a title like "Why?" must not be read as a regular expression
    in_title = books["title"].str.contains(query, case=False, regex=False)
    in_authors = books["authors"].str.contains(query, case=False, regex=False)
    found = books[in_title | in_authors]
    return found.nlargest(max_results, "ratings_count")


def save_table(table, name, results_dir=RESULTS_DIR):
    """
    Save a table of results as a CSV file.

    Parameters
    ----------
    table : pandas.DataFrame
        The table to save.
    name : str
        Name of the file, without the extension.
    results_dir : str, optional
        Folder of the results (created if it doesn't exist).

    Returns
    -------
    str
        The path of the saved file.
    """
    os.makedirs(results_dir, exist_ok=True)
    path = os.path.join(results_dir, name + ".csv")
    table.to_csv(path, index=False)
    return path
