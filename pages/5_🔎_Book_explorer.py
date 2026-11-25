"""Page of the app: look up a book, and save it in the reading list."""

import pandas as pd
import streamlit as st

import app_utils
from goodbooks import analysis, data, interactive

app_utils.setup_page("Book explorer", "🔎")
books = app_utils.get_books()

st.header("🔎 Book explorer")
query = st.text_input("Search a title or an author", "Tolkien")
found = data.find_books(books, query)
if found.empty:
    st.warning(f"No book matches “{query}”.")
    st.stop()

labels = {
    row["book_id"]: f"{row['title']} ({row['main_author']})"
    for _, row in found.iterrows()
}
book_id = st.selectbox(
    f"{len(found)} books found (the most rated first)",
    list(labels),
    format_func=labels.get,
)
book = books[books["book_id"] == book_id].iloc[0]

# --- The book ---
cover, details = st.columns([1, 4])
if app_utils.has_cover(book["image_url"]):
    cover.image(book["image_url"], width=150)
details.subheader(book["short_title"])
year = "unknown year" if pd.isna(book["year"]) else book["year"]
details.write(f"by **{book['authors']}** · {year} · {book['genre']}")

genre_mean = books.loc[books["genre"] == book["genre"], "average_rating"].mean()
metrics = details.columns(3)
metrics[0].metric(
    "Average rating",
    f"{book['average_rating']:.2f} ★",
    delta=f"{book['average_rating'] - genre_mean:+.2f} vs its genre",
)
metrics[1].metric("Ratings", f"{book['ratings_count']:,}")
metrics[2].metric("Divisiveness", f"{book['star_std']:.2f}")

if details.button("➕ Add to my reading list"):
    app_utils.add_to_reading_list(book_id)
    details.success("Added: it stays in the sidebar on every page.")

# --- How readers rated it, next to the books of the reading list ---
saved = app_utils.reading_list_books(books)
to_plot = books[books["book_id"].isin([book_id, *saved["book_id"]])]
st.plotly_chart(interactive.star_bars(analysis.star_shares_long(to_plot)))
if len(to_plot) == 1:
    st.caption("Add books to your reading list to compare them here.")

# Last: the sidebar must also show a book added by the button above
app_utils.reading_list_sidebar(books)
