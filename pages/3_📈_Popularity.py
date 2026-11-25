"""Page of the app: are popular books also the most appreciated?"""

import streamlit as st

import app_utils
from goodbooks import analysis, interactive

TOP_COLUMNS = [
    "short_title",
    "main_author",
    "year",
    "genre",
    "average_rating",
    "ratings_count",
    "weighted_rating",
]

app_utils.setup_page("Popularity", "📈")
books = app_utils.get_books()

st.header("📈 Are popular books also the most appreciated?")
all_genres = sorted(books["genre"].unique())
genres = st.sidebar.multiselect("Genres", all_genres, default=all_genres)
n_books = st.sidebar.slider("Number of best-loved books", 5, 50, 15)
app_utils.reading_list_sidebar(books)

selected = books[books["genre"].isin(genres)]
if selected.empty:
    st.warning("Select at least one genre.")
    st.stop()

st.write(
    "Each point is a book: hover over it to see its title, click on a genre "
    "in the legend to hide it, drag to zoom (double click to zoom out)."
)
st.plotly_chart(interactive.popularity_scatter(selected))
result = analysis.correlation(selected["log_ratings_count"], selected["average_rating"])
st.write(
    f"Spearman correlation between the number of ratings and the average "
    f"rating: **{result['rho']:.2f}** ({result['n']:,} books). "
    "Popularity says very little about appreciation."
)

st.subheader("The best-loved books (weighted rating)")
top_books = selected[~selected["is_compilation"]].nlargest(n_books, "weighted_rating")
st.dataframe(top_books[TOP_COLUMNS].round(3), hide_index=True)
