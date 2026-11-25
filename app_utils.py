"""
Helpers shared by the pages of the Streamlit app.

Every page of a multi-page app is a separate script: the data loading, the
error handling and the reading list live here, so that they are written once.
The analysis itself stays in the goodbooks package.
"""

import matplotlib.pyplot as plt
import requests
import seaborn as sns
import streamlit as st

from goodbooks import data

# A placeholder that Goodreads uses for the books without a cover
NO_COVER = "nophoto"


def setup_page(title, icon):
    """Configure the page (title of the browser tab, icon, wide layout)."""
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")
    sns.set_theme(style="whitegrid")


@st.cache_data(show_spinner="Loading 10,000 books...")
def load_books():
    """Download the dataset if needed, and load the clean books (only once)."""
    data.download_dataset()  # does nothing if the files are already in data/
    return data.load_books()


def get_books():
    """
    Return the books, or stop the page with a clear message if they can't be loaded.

    Returns
    -------
    pandas.DataFrame
        The output of ``data.load_books``.
    """
    try:
        return load_books()
    except (
        FileNotFoundError,
        ValueError,
        requests.exceptions.RequestException,
    ) as error:
        st.error(f"Could not load the dataset: {error}")
        st.write(
            "Put the CSV files of goodbooks-10k in the `data/` folder "
            "(see the README), then reload the page."
        )
        st.stop()


def show(fig):
    """Show a matplotlib figure, then close it to free the memory."""
    st.pyplot(fig)
    plt.close(fig)


def has_cover(image_url):
    """Return True if the book has a real cover, not the Goodreads placeholder."""
    return isinstance(image_url, str) and NO_COVER not in image_url


# --- Reading list, kept in the session state across pages and reruns ---
def init_reading_list():
    """Create an empty reading list the first time the session runs a page."""
    if "reading_list" not in st.session_state:
        st.session_state.reading_list = []  # book_id of the saved books


def add_to_reading_list(book_id):
    """Add a book to the reading list, unless it is already there."""
    init_reading_list()
    if book_id not in st.session_state.reading_list:
        st.session_state.reading_list.append(book_id)


def reading_list_books(books):
    """Return the rows of the books in the reading list, in the order they were added."""
    init_reading_list()
    saved = books.set_index("book_id").loc[st.session_state.reading_list]
    return saved.reset_index()


def reading_list_sidebar(books):
    """Show the reading list in the sidebar, with a button to empty it."""
    init_reading_list()
    st.sidebar.subheader("📖 My reading list")
    saved = reading_list_books(books)
    if saved.empty:
        st.sidebar.caption("Empty: add books from the Book explorer page.")
        return
    for _, book in saved.iterrows():
        st.sidebar.write(f"- {book['short_title']} ({book['average_rating']:.2f} ★)")
    if st.sidebar.button("Empty the list"):
        st.session_state.reading_list = []
        st.rerun()
