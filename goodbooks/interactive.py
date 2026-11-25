"""
Interactive charts of the web app (Plotly Express).

The charts of ``plots.py`` are images, made for the notebook. These ones are
drawn in the browser: the reader can hover over a point to see which book it
is, zoom, and hide a genre by clicking on the legend. Like in ``plots.py``,
each function only returns the figure: the app shows it with
``st.plotly_chart(fig)``.
"""

import plotly.express as px

from goodbooks.plots import STAR_COLORS

# The names of the columns, as the reader sees them in the charts
LABELS = {
    "average_rating": "Average rating",
    "ratings_count": "Number of ratings",
    "main_author": "Author",
    "short_title": "Title",
    "year": "Publication year",
    "genre": "Genre",
    "star_std": "Divisiveness (std of the stars)",
    "weighted_rating": "Weighted rating",
    "book_number": "Book number",
}


def popularity_scatter(books):
    """
    Average rating against the number of ratings, one point per book.

    Parameters
    ----------
    books : pandas.DataFrame
        One row per book.

    Returns
    -------
    plotly.graph_objects.Figure
        Points coloured by genre; the title of the book appears on hover.
    """
    fig = px.scatter(
        books,
        x="ratings_count",
        y="average_rating",
        color="genre",
        log_x=True,  # from a few thousands to millions of ratings
        opacity=0.6,
        hover_name="short_title",
        hover_data={"main_author": True, "year": True, "genre": False},
        labels=LABELS,
        title="Popularity and appreciation of the books",
    )
    fig.update_traces(marker={"size": 5})
    return fig

##A trace is Plotly's name for one set of plotted data. With color="genre", 
# each genre is its own trace.
##update_traces(...) changes all of them at once.
##marker={"size": 5} sets the dot size to 5 pixels, small enough that 10,000 dots don't become one blob.

def genre_box(books, order):
    """
    Box plots of the average ratings of each genre.

    Parameters
    ----------
    books : pandas.DataFrame
        One row per book, with ``genre`` and ``average_rating``.
    order : list of str
        The genres to show, from top to bottom.

    Returns
    -------
    plotly.graph_objects.Figure
        One box per genre; hovering over an outlier shows the book.
    """
    fig = px.box(
        books[books["genre"].isin(order)],
        x="average_rating",
        y="genre",
        color="genre",
        category_orders={"genre": order},
        hover_name="short_title",
        labels=LABELS,
        title="Spread of the ratings by genre",
    )
    fig.update_layout(showlegend=False, height=550)
    return fig


def genre_era_heatmap(table, overall_mean):
    """
    Heatmap of the mean rating of each genre in each publication era.

    Parameters
    ----------
    table : pandas.DataFrame
        Output of ``analysis.genre_era_table``.
    overall_mean : float
        Mean rating of all the books: the white of the colour scale.

    Returns
    -------
    plotly.graph_objects.Figure
        Blue cells are above the mean of all the books, red ones below; empty
        cells have too few books.
    """
    fig = px.imshow(
        table,
        text_auto=".2f",
        color_continuous_scale="RdBu",
        color_continuous_midpoint=overall_mean,
        aspect="auto",
        labels={"x": "Publication era", "y": "", "color": "Mean rating"},
        title="Mean rating by genre and era",
    )
    fig.update_layout(height=550)
    return fig


def author_timeline(works, authors):
    """
    The ratings of some authors, book after book, by publication year.

    Parameters
    ----------
    works : pandas.DataFrame
        Output of ``analysis.author_works``.
    authors : list of str
        The authors to show.

    Returns
    -------
    plotly.graph_objects.Figure
        One line per author; hovering over a point shows the title.
    """
    selected = works[works["main_author"].isin(authors)]
    fig = px.line(
        selected,
        x="year",
        y="average_rating",
        color="main_author",
        markers=True,
        hover_name="short_title",
        hover_data={"ratings_count": ":,", "main_author": False},
        labels=LABELS,
        title="Ratings across each author's works",
    )
    return fig


def star_bars(shares):
    """
    Stacked bars of the share of 1-5 star ratings of some books.

    Parameters
    ----------
    shares : pandas.DataFrame
        Output of ``analysis.star_shares_long``.

    Returns
    -------
    plotly.graph_objects.Figure
        One horizontal bar per book, from 1 star (red) to 5 stars (blue).
    """
    # Discrete colours need the stars as text, not numbers
    shares = shares.assign(stars=shares["stars"].astype(str) + "★")
    colors = {f"{stars}★": color for stars, color in zip(range(1, 6), STAR_COLORS)}
    fig = px.bar(
        shares,
        x="share",
        y="title",
        color="stars",
        orientation="h",
        color_discrete_map=colors,
        labels={"share": "Share of the ratings (%)", "title": "", "stars": ""},
        title="How the readers rated it",
    )
    fig.update_traces(hovertemplate="%{x:.1f}%")
    fig.update_layout(height=150 + 40 * shares["title"].nunique())
    return fig
