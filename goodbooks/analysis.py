"""
Statistics on the ratings of the books (pandas, NumPy and SciPy).

* Are some genres rated higher?           -> group_statistics, compare_with_rest
* Are older books rated differently?      -> group_statistics, year_trend,
                                             genre_era_table
* How do the readers of a book split?     -> star_shares_long
* Are popular books the most appreciated? -> correlation, weighted_rating
* How do an author's ratings evolve?      -> author_works, author_slopes
* How do readers rate?                    -> user_summary
"""

import numpy as np
import pandas as pd
from scipy import stats

# An author needs at least this many books to be followed over time
MIN_BOOKS_PER_AUTHOR = 5


def weighted_rating(average, count, min_votes=None):
    """
    Weighted rating, which pulls the books with few ratings toward the global mean.

    ``WR = v / (v + m) * R + m / (v + m) * C``, where ``R`` is the average
    rating of the book, ``v`` its number of ratings, ``C`` the mean rating of
    all the books and ``m`` the weight of the global mean.

    Parameters
    ----------
    average : pandas.Series
        Average rating of each book (R).
    count : pandas.Series
        Number of ratings of each book (v).
    min_votes : float, optional
        The weight m. Defaults to the median of count.

    Returns
    -------
    pandas.Series
        The weighted rating of each book.
    """
    m = np.median(count) if min_votes is None else min_votes
    c = np.mean(average)
    return count / (count + m) * average + m / (count + m) * c
## This is the formula, applied to every book at once. 
# count and average are whole Series, and pandas does the arithmetic 
# element by element (this is called vectorisation, so there's no loop).
#  The two weights, v/(v+m) and m/(v+m), always add up to 1.

def group_statistics(books, group, value="average_rating", min_size=30):
    """
    Statistics of a column for each group, with a 95% confidence interval of the mean.

    Parameters
    ----------
    books : pandas.DataFrame
        One row per book.
    group : str
        The column with the groups, e.g. ``"genre"`` or ``"era"``.
    value : str, optional
        The column to summarise.
    min_size : int, optional
        The groups with fewer books are dropped.

    Returns
    -------
    pandas.DataFrame
        One row per group: ``n_books``, ``mean``, ``median``, ``std``,
        ``ci_low`` and ``ci_high``.
    """
    table = (
        books.groupby(group, observed=True)[value]
        .agg(n_books="size", mean="mean", median="median", std="std")
        .reset_index()
    )
    
    table = table[table["n_books"] >= min_size]
    # With 30 or more books (drop small groups), 
    # add a 95% confidence interval for each group's mean
    # the mean is about normal: mean +- 1.96 standard errors
    half_width = 1.96 * table["std"] / np.sqrt(table["n_books"])
    return table.assign(
        ci_low=table["mean"] - half_width, ci_high=table["mean"] + half_width
    )

# this function builds a grid: one row per genre, one column per era, and in each cell the average
# rating of the books in that genre and era. Cells based on too few books are left empty, and
# genres are sorted from best-rated to worst. 
def genre_era_table(books, min_books=10):
    """
    Mean rating of each genre in each publication era, as a genre x era table.

    Parameters
    ----------
    books : pandas.DataFrame
        Books with ``genre``, ``era`` and ``average_rating``.
    min_books : int, optional
        A cell with fewer books is left empty (NaN): its mean is not reliable.

    Returns
    -------
    pandas.DataFrame
        One row per genre and one column per era, sorted from the genre with
        the highest mean rating.
    """
    # Long format (one row per genre and era) -> wide format (eras as columns)
    table = books.pivot_table(
        index="genre",
        columns="era",
        values="average_rating",
        aggfunc=["mean", "size"],
        observed=False, # keep every era, even empty ones
    )
    # pandas groups the books by genre and era together. For each combination it computes:
    means = table["mean"].where(table["size"] >= min_books)
    order = books.groupby("genre")["average_rating"].mean().sort_values().index
    return means.reindex(order[::-1]).dropna(how="all")

# groups all books by genre, ignoring era. 
# gives each genre's overall average
# sorts it lowest first
# keeps only the names, not the numbers ["Romance", "Poetry", "Fantasy"]

## order[::-1] reverses the list, so it becomes ["Fantasy", "Poetry", 
# "Romance"] with the best first. ([::-1] is Python's "go backwards"
# slice.)
## .reindex(...) rearranges the rows into that order.
## .dropna(how="all") removes a row only if every cell in it is NaN.
#A genre with too few books in every era would be an empty row, 
# so it's dropped. Rows with some values stay.

#This function takes each book's star counts (how many people gave 
# 1 star, 2 stars and so on) and turns them into percentages. 
# Then it reshapes the result into a tall "long" table with one row 
# per book per star level, which is the shape plotting tools want.
def star_shares_long(books, title_column="short_title"):
    """
    The share of 1, 2, 3, 4 and 5 star ratings of some books, in long format.

    Parameters
    ----------
    books : pandas.DataFrame
        The books, with the columns ``ratings_1`` ... ``ratings_5``.
    title_column : str, optional
        The column that names each book.

    Returns
    -------
    pandas.DataFrame
        One row per (book, stars): ``title``, ``stars`` (1-5) and
        ``share`` (percentage of the ratings of the book).
    """
    star_columns = [f"ratings_{stars}" for stars in range(1, 6)]
    counts = books[star_columns].to_numpy(dtype=float)
    # Divide each row by its total: broadcasting of a (n, 1) column over (n, 5)
    shares = counts / counts.sum(axis=1, keepdims=True) * 100
    wide = pd.DataFrame(shares, columns=range(1, 6))
    wide["title"] = books[title_column].to_numpy()
    return wide.melt(id_vars="title", var_name="stars", value_name="share")

##books[star_columns] selects just those 5 columns.
##.to_numpy(dtype=float) converts them from a pandas table into 
# a NumPy array, a bare grid of numbers with no labels, stored as 
# decimals (float) so the division later gives exact decimals.

# counts.sum(axis=1) adds across each row (axis=1 means 
# across the columns; axis=0 would add down each column)

#keepdims=True: keep it as a column; 

#melt "unpivots" the table

def compare_with_rest(books, group, value="average_rating", min_size=30):
    """
    Are books in this genre rated differently from all the other books?
    Compare the books of each group with all the other books.

    The Mann-Whitney U test doesn't assume normal data, so it suits ratings.

    Parameters
    ----------
    books, group, value, min_size
        As in ``group_statistics``.

    Returns
    -------
    pandas.DataFrame
        One row per group: 
        ``difference`` (mean of the group minus mean ofthe other books) 
        how much higher or lower the genre's average is than everyone else's
        and ``p_value``, how likely a gap that size would be by pure chance.
    """
    rows = []
    for name, in_group in books.groupby(group, observed=True):
        if len(in_group) < min_size:
            continue
        others = books.loc[books[group] != name, value]
        result = stats.mannwhitneyu(in_group[value], others)
        rows.append(
            {
                group: name,
                "difference": in_group[value].mean() - others.mean(),
                "p_value": result.pvalue,
            }
        )
    return pd.DataFrame(rows)
# name: the group's label, e,g. "Fantasy"
# in_group --> a smaller table contaning only that group's books

#1. Why test at all?
#Say Fantasy averages 4.10 and the other books average 4.05. 
# Is Fantasy really rated higher, or is that just noise?

#Any group of books will have a slightly different average from the 
# rest, even if genre makes no difference at all. If you randomly 
# split books into two piles, the averages would almost never match 
# exactly. So looking at the difference alone can't tell you whether 
# it's real or luck.

#A statistical test answers that. It gives the p-value: how often 
# a gap this big would happen by chance if the genre made no real 
# difference. Without it, you might report "Fantasy is rated higher" 
# when the gap is meaningless

# 2. Why Mann–Whitney U specifically?
#The most common test for comparing two groups is the t-test. 
# It compares averages directly, but it works best when the data 
# is roughly a bell curve and has no extreme values.
# Book ratings don't look like that:
# They're bunched up, with most books between about 3.7 and 4.3.
# They're lopsided, with a long tail of badly rated books on the low side.
# A few outliers (a book averaging 2.1, say) can drag an average around.
#Mann–Whitney U avoids these problems by working with ranks instead of the 
# actual numbers. It lines up all the ratings from lowest to highest and
#  asks whether this genre's books tend to sit higher in the line than 
# the others. Because only the order matters, a single extreme rating 
# can't distort the result, and the shape of the data doesn't matter.

def correlation(x, y):
    """
    Spearman correlation between two columns, ignoring the missing values.
    it measures how well two rankings agree. 
    What sets it apart is that it doesn't use the actual values. 
    It replaces them with ranks (1st, 2nd, 3rd…) and compares those.

    Returns
    -------
    dict
        ``rho`` (the coefficient), ``p_value`` and ``n`` (the number of rows).
    """
    pair = pd.concat([x, y], axis=1).dropna()
    result = stats.spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
    return {"rho": result.statistic, "p_value": result.pvalue, "n": len(pair)}

#This function answers: are newer books rated higher or lower than 
# older ones? It draws the best-fitting straight line through all the 
# books (year on the x-axis, rating on the y-axis) and reports how 
# steep that line is and how well it fits.
def year_trend(books, start_year=1900):
    """
    Least squares line through the average ratings against the publication year.

    Parameters
    ----------
    books : pandas.DataFrame
        Books with ``year`` and ``average_rating``.
    start_year : int, optional
        Only the books published in this year or later are used.

    Returns
    -------
    dict
        ``slope`` (stars per year), ``intercept``, ``r_squared``, ``p_value``
        and ``n`` (the number of books).
    """
    data = books.loc[books["year"] >= start_year, ["year", "average_rating"]]
    data = data.dropna()
    trend = stats.linregress(data["year"].astype(float), data["average_rating"])
    return {
        "slope": trend.slope,
        "intercept": trend.intercept,
        "r_squared": trend.rvalue**2,
        "p_value": trend.pvalue,
        "n": len(data),
    }

# .astype(float) converts the years to decimal numbers. Years are often 
# stored in special integer types that can cause errors or overflow in 
# the calculation, so this is a safety step.

# how do an author's ratings change over their career?"
def author_works(books, min_books=MIN_BOOKS_PER_AUTHOR):
    """
    The books of the authors with at least min_books books, in order of publication.

    Box sets and collections are left out, since they are not new works,
    and so are the second editions of the same title.

    Parameters
    ----------
    books : pandas.DataFrame
        Books with ``main_author``, ``year``, ``is_compilation`` and
        ``average_rating``.
    min_books : int, optional
        Minimum number of books with a known year.

    Returns
    -------
    pandas.DataFrame
        The books of these authors, with ``book_number`` (1 for the first one).
    """
    works = books[~books["is_compilation"]].dropna(subset=["year"])
    # Some books appear twice, as two editions: keep one
    works = works.drop_duplicates(subset=["main_author", "short_title"])
    works = works.sort_values(["main_author", "year"])
    n_books = works.groupby("main_author")["book_id"].transform("size")
    works = works[n_books >= min_books].copy()
    # keep only author with enough books
    works["book_number"] = works.groupby("main_author").cumcount() + 1
    return works

## ~ -> flips True to False and vice versa
## .transform("size") counts the rows in 
# each group and then writes that count onto every row of the group.

# .copy() -> makes works a fully independent table. Without it, 
# pandas may treat the filtered result as a "view" of the old one, 
# and adding a column in the next line would trigger a 
# SettingWithCopyWarning. .copy() avoids that.


def author_slopes(works):
    """
    Fit a straight line through the ratings of each author, book after book.
    The slope of that line says whether the author's books get better or 
    worse ratings over their career. It returns one summary row per 
    author.

    Parameters
    ----------
    works : pandas.DataFrame
        Output of ``author_works``.

    Returns
    -------
    pandas.DataFrame
        One row per author: ``n_books``, ``mean_rating``, ``slope`` (change
        in rating per new book) and ``total_ratings``, the most read first.
    """
    rows = []
    for author, books_of_author in works.groupby("main_author"):
        # A line of degree 1: polyfit returns [slope, intercept]
        # Degree 2 would be a curve, a parabola.
        slope, _ = np.polyfit(
            books_of_author["book_number"], books_of_author["average_rating"], 1
        )
        # slope, _ = ... is called unpacking: 
        # the two returned values are put into two variables at once.

        #_ is the name Python programmers use for a value they don't need. 
        # The intercept isn't used, so it goes into _ and is ignored.
        rows.append(
            {
                "main_author": author,
                "n_books": len(books_of_author),
                "mean_rating": books_of_author["average_rating"].mean(),
                "slope": slope,
                "total_ratings": books_of_author["ratings_count"].sum(),
            }
        )
    return pd.DataFrame(rows).sort_values("total_ratings", ascending=False)

# np.polyfit(x, y, degree) finds the best-fitting 
# polynomial through the points, using least squares,

def user_summary(ratings):
    """
    Summarise the ratings of each user.

    Returns
    -------
    pandas.DataFrame
        One row per user: ``user_id``, ``n_ratings`` and ``mean_rating``.
    """
    return (
        ratings.groupby("user_id")["rating"]
        .agg(n_ratings="size", mean_rating="mean")
        .reset_index()
    )

# This moves user_id from the index into 
# a regular column and gives the rows a fresh 0, 1, 2… index