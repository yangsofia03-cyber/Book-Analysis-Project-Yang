"""
Charts of the analysis (matplotlib and seaborn).

Each function returns a matplotlib Figure: a notebook shows it below the
cell, the Streamlit app shows it with ``st.pyplot(fig)``, and
``save_figure`` writes it to the results folder.
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

MAIN_COLOR = "#2a78d6"  # blue
SECOND_COLOR = "#eb6834"  # orange
GREY = "#8a8984"
# From 1 star (red) to 5 stars (blue)
STAR_COLORS = ["#e34948", "#eb6834", "#b9b8b2", "#6da7ec", "#2a78d6"]


def save_figure(fig, name, results_dir):
    """
    Save a figure as a PNG file in results_dir (created if it doesn't exist).

    Returns
    -------
    str
        The path of the saved file.
    """
    os.makedirs(results_dir, exist_ok=True)
    path = os.path.join(results_dir, name + ".png")
    fig.savefig(path, dpi=150)
    return path


def rating_histogram(books):
    """Histogram of the average ratings of the books, with their mean."""
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    ax.hist(books["average_rating"], bins=50, color=MAIN_COLOR, edgecolor="white")
    mean = books["average_rating"].mean()
    ax.axvline(mean, color="black", linestyle="--", label=f"mean ({mean:.2f})")
    ax.set_xlabel("Average rating (1-5 stars)")
    ax.set_ylabel("Number of books")
    ax.set_title("Distribution of the average ratings of the 10,000 books")
    ax.legend()
    return fig


def star_shares(ratings):
    """Bar chart of the share of the individual ratings with 1, 2, 3, 4 and 5 stars."""
    shares = ratings["rating"].value_counts(normalize=True).sort_index() * 100
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    bars = ax.bar([f"{stars}★" for stars in shares.index], shares, color=STAR_COLORS)
    ax.bar_label(bars, fmt="%.0f%%", padding=3)
    ax.set_ylim(0, shares.max() * 1.15)  # room for the labels above the bars
    ax.set_ylabel("Share of the ratings (%)")
    ax.set_title("What readers give: the 6 million individual ratings")
    return fig


def genre_means(table, overall_mean):
    """
    Mean rating of each genre, with its 95% confidence interval.

    Parameters
    ----------
    table : pandas.DataFrame
        Output of ``analysis.group_statistics`` with ``group="genre"``.
    overall_mean : float
        Mean rating of all the books, drawn as a dashed line.
    """
    table = table.sort_values("mean")
    # Blue: clearly above the mean of all books; orange: clearly below;
    # grey: the confidence interval contains the mean
    colors = np.where(
        table["ci_low"] > overall_mean,
        MAIN_COLOR,
        np.where(table["ci_high"] < overall_mean, SECOND_COLOR, GREY),
    )

    fig, ax = plt.subplots(figsize=(8, 6), layout="constrained")
    # Dots and error bars, not bars: bars should start at 0, which would hide
    # the differences between the genres
    for (_, row), color in zip(table.iterrows(), colors):
        ax.errorbar(
            row["mean"],
            row["genre"],
            xerr=[[row["mean"] - row["ci_low"]], [row["ci_high"] - row["mean"]]],
            fmt="o",
            color=color,
            capsize=3,
        )
    ax.axvline(overall_mean, color="black", linestyle="--", label="all books")
    ax.set_xlabel("Mean of the average ratings (95% confidence interval)")
    ax.set_title("Mean rating by genre")
    ax.legend(loc="lower right")
    return fig


def genre_boxplot(books, order):
    """Box plots of the average ratings of each genre: the spread, not only the mean."""
    fig, ax = plt.subplots(figsize=(8, 6), layout="constrained")
    sns.boxplot(
        data=books[books["genre"].isin(order)],
        x="average_rating",
        y="genre",
        order=order,
        color="#b7d3f6",
        fliersize=2,
        ax=ax,
    )
    ax.axvline(books["average_rating"].median(), color=SECOND_COLOR, linestyle="--")
    ax.set_xlabel("Average rating")
    ax.set_ylabel("")
    ax.set_title("Spread of the ratings by genre (dashed line: median of all books)")
    return fig


def era_means(era_table):
    """Mean rating of each publication era, with its 95% confidence interval."""
    errors = [
        era_table["mean"] - era_table["ci_low"],
        era_table["ci_high"] - era_table["mean"],
    ]
    labels = [
        f"{era}\n({n:,} books)"
        for era, n in zip(era_table["era"], era_table["n_books"])
    ]
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    ax.errorbar(
        labels, era_table["mean"], yerr=errors, fmt="o-", color=MAIN_COLOR, capsize=4
    )
    ax.set_ylabel("Mean of the average ratings")
    ax.set_title("Mean rating by publication era (95% confidence interval)")
    return fig


def year_scatter(books, trend, start_year=1900):
    """Average ratings against the publication year, with the line of ``year_trend``."""
    data = books[books["year"] >= start_year].dropna(subset=["year"])
    years = np.array([start_year, data["year"].max()], dtype=float)

    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    ax.scatter(data["year"], data["average_rating"], s=5, alpha=0.3, color=GREY)
    ax.plot(
        years,
        trend["intercept"] + trend["slope"] * years,
        color=SECOND_COLOR,
        linewidth=2,
        label=f"linear trend: {trend['slope'] * 10:+.3f} stars per decade",
    )
    ax.set_xlabel("Original publication year")
    ax.set_ylabel("Average rating")
    ax.set_title(f"Average rating by publication year (books since {start_year})")
    ax.legend(loc="lower left")
    return fig


def popularity_scatter(books):
    """Average rating against the number of ratings (log scale), with a regression line."""
    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    sns.regplot(
        data=books,
        x="log_ratings_count",
        y="average_rating",
        scatter_kws={"s": 5, "alpha": 0.3, "color": GREY},
        line_kws={"color": MAIN_COLOR},
        ax=ax,
    )
    ax.set_xlabel("Number of ratings (log10: 4 = 10,000, 6 = 1,000,000)")
    ax.set_ylabel("Average rating")
    ax.set_title("Are popular books also the most appreciated?")
    return fig


def correlation_heatmap(books, columns):
    """
    Heatmap of the Spearman correlations between some columns.

    Parameters
    ----------
    books : pandas.DataFrame
        One row per book.
    columns : dict
        Mapping ``column -> label`` of the columns to compare.
    """
    correlations = books[list(columns)].rename(columns=columns).corr(method="spearman")
    fig, ax = plt.subplots(figsize=(6.5, 5.5), layout="constrained")
    sns.heatmap(
        correlations, annot=True, fmt=".2f", cmap="RdBu", vmin=-1, vmax=1, ax=ax
    )
    ax.set_title("Spearman correlations between the book metrics")
    return fig


def author_lines(works, authors):
    """The ratings of a few authors, book after book, in order of publication."""
    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    for author in authors:
        books_of_author = works[works["main_author"] == author]
        ax.plot(
            books_of_author["book_number"],
            books_of_author["average_rating"],
            "o-",
            label=f"{author} ({len(books_of_author)} books)",
        )
    ax.set_xlabel("Book number, in order of publication")
    ax.set_ylabel("Average rating")
    ax.set_title("Ratings across each author's works")
    ax.legend()
    return fig


def slope_histogram(slopes):
    """Histogram of the slopes of ``author_slopes``: do authors improve?"""
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    # A few authors with few books have extreme slopes: cut them for the plot
    ax.hist(
        slopes["slope"].clip(-0.15, 0.15), bins=40, color=MAIN_COLOR, edgecolor="white"
    )
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel("Change in rating per new book (cut at +-0.15)")
    ax.set_ylabel("Number of authors")
    ax.set_title(f"Do authors improve? The trend of {len(slopes)} authors")
    return fig


def user_scatter(users):
    """Number of books rated by each user against their mean rating."""
    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    ax.scatter(
        users["n_ratings"], users["mean_rating"], s=3, alpha=0.1, color=MAIN_COLOR
    )
    ax.set_xlabel("Number of books rated by the user")
    ax.set_ylabel("Mean rating given by the user")
    ax.set_title("Do readers who rate more books rate differently?")
    return fig
