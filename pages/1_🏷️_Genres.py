"""Page of the app: are some genres rated higher?"""

import streamlit as st

import app_utils
from goodbooks import analysis, interactive, plots

app_utils.setup_page("Genres", "🏷️")
books = app_utils.get_books()

st.header("🏷️ Are some genres rated higher?")
min_size = st.sidebar.slider("Minimum number of books per genre", 10, 300, 30)
app_utils.reading_list_sidebar(books)

table = analysis.group_statistics(books, "genre", min_size=min_size)
table = table.merge(
    analysis.compare_with_rest(books, "genre", min_size=min_size), on="genre"
)
table = table.sort_values("mean", ascending=False)

app_utils.show(plots.genre_means(table, books["average_rating"].mean()))
st.write(
    "Blue genres are clearly above the mean of all books, orange ones clearly "
    "below (95% confidence interval). The p-value compares each genre with "
    "all the other books (Mann-Whitney U test)."
)
st.dataframe(table.round(3), hide_index=True)

st.subheader("Is the difference consistent?")
st.write(
    "The box shows where the middle half of the books of each genre lies. "
    "Hover over a point to see which book it is."
)
st.plotly_chart(interactive.genre_box(books, list(table["genre"])))
