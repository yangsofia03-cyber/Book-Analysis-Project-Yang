"""Page of the app: are older books rated differently from recent ones?"""

import streamlit as st

import app_utils
from goodbooks import analysis, interactive, plots

MIN_BOOKS_FOR_TREND = 20

app_utils.setup_page("Old vs recent", "🕰️")
books = app_utils.get_books()

st.header("🕰️ Are older books rated differently?")
genres = ["All genres"] + sorted(books["genre"].unique())
genre = st.sidebar.selectbox("Genre", genres)
start_year = st.sidebar.slider("Books published from", 1800, 2000, 1900, step=10)
app_utils.reading_list_sidebar(books)

selected = books if genre == "All genres" else books[books["genre"] == genre]

app_utils.show(plots.era_means(analysis.group_statistics(selected, "era", min_size=10)))

if (selected["year"] >= start_year).sum() < MIN_BOOKS_FOR_TREND:
    st.warning("Too few books in this selection for a trend line.")
else:
    trend = analysis.year_trend(selected, start_year)
    app_utils.show(plots.year_scatter(selected, trend, start_year))
    st.write(
        f"Linear trend: **{trend['slope'] * 10:+.3f} stars per decade** "
        f"(R² = {trend['r_squared']:.3f}, {trend['n']:,} books)."
    )

st.subheader("Genre and era together")
st.write(
    "Each cell is the mean rating of the books of a genre in an era: blue "
    "above the mean of all the books, red below. Empty cells have fewer than "
    "10 books."
)
st.plotly_chart(
    interactive.genre_era_heatmap(
        analysis.genre_era_table(books), books["average_rating"].mean()
    )
)
