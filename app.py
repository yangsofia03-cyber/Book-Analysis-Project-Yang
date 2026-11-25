"""
Streamlit app: what makes a book loved by readers?

Run it from the root of the project with:  streamlit run app.py

This is the home page; the other pages are the scripts in ``pages/``, which
Streamlit lists in the sidebar. The app only shows the results: loading,
cleaning, statistics and charts come from the goodbooks package, like in
the notebook.
"""

import streamlit as st

import app_utils
from goodbooks import plots

N_COVERS = 6  # the best-loved books shown with their cover

app_utils.setup_page("What makes a book loved?", "📚")
books = app_utils.get_books()
app_utils.reading_list_sidebar(books)

st.title("📚 What makes a book loved by readers?")
st.write(
    "This app explores **goodbooks-10k**: the 10,000 most popular books on "
    "Goodreads, with about 6 million ratings and the tags readers gave them. "
    "Use the pages in the sidebar to see how genre, publication year, "
    "popularity and author go together with the average rating of a book, "
    "or look up a single book in the **Book explorer**."
)

# --- Key numbers ---
columns = st.columns(4)
columns[0].metric("Books", f"{len(books):,}")
columns[1].metric("Authors", f"{books['main_author'].nunique():,}")
columns[2].metric("Ratings on Goodreads", f"{books['ratings_count'].sum() / 1e6:.0f} M")
columns[3].metric("Mean rating", f"{books['average_rating'].mean():.2f} ★")

# --- The best-loved books, with their covers ---
st.subheader("🏆 The best-loved books")
st.caption(
    "Ranked by weighted rating, which doesn't let a book with few ratings "
    "win by chance (box sets and collections excluded)."
)
top_books = books[~books["is_compilation"]].nlargest(N_COVERS, "weighted_rating")
for column, (_, book) in zip(st.columns(N_COVERS), top_books.iterrows()):
    if app_utils.has_cover(book["image_url"]):
        column.image(book["image_url"], width=110)
    column.markdown(f"**{book['short_title']}**")
    column.caption(f"{book['main_author']} · {book['average_rating']:.2f} ★")

# --- Distribution of the ratings ---
st.subheader("How are the ratings distributed?")
app_utils.show(plots.rating_histogram(books))
st.write(
    "Average ratings are high and concentrated: half of the books are between "
    "3.85 and 4.18 stars, and very few go below 3.5."
)

if st.checkbox("Show the data"):
    st.dataframe(books.head(100), hide_index=True)
