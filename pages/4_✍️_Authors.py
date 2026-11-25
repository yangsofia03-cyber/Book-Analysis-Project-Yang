"""Page of the app: how do the ratings of an author evolve across their works?"""

import streamlit as st

import app_utils
from goodbooks import analysis, interactive, plots

DEFAULT_AUTHORS = ["J.K. Rowling", "Suzanne Collins", "Stephenie Meyer"]

app_utils.setup_page("Authors", "✍️")
books = app_utils.get_books()
app_utils.reading_list_sidebar(books)

st.header("✍️ How do authors' ratings evolve?")
works = analysis.author_works(books)
slopes = analysis.author_slopes(works)

authors = st.multiselect(
    f"Authors (with at least {analysis.MIN_BOOKS_PER_AUTHOR} books)",
    slopes["main_author"],
    default=[
        author for author in DEFAULT_AUTHORS if author in set(slopes["main_author"])
    ],
)
if authors:
    st.plotly_chart(interactive.author_timeline(works, authors))
    chosen = slopes[slopes["main_author"].isin(authors)]
    st.dataframe(chosen.round(3), hide_index=True)
else:
    st.info("Choose one or more authors.")

st.subheader("Do authors improve in general?")
columns = st.columns(3)
columns[0].metric("Authors followed", f"{len(slopes):,}")
columns[1].metric("Authors who improve", f"{(slopes['slope'] > 0).mean():.0%}")
columns[2].metric("Median change per book", f"{slopes['slope'].median():+.3f} ★")
app_utils.show(plots.slope_histogram(slopes))
