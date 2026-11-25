"""
Turn the user tags of Goodreads into genres.

Readers shelve books with free tags: the most common ones, like ``to-read``
or ``favorites``, say nothing about the genre, and the same genre has many
spellings (``sci-fi``, ``scifi``, ``science-fiction``). We map a few tags to
each genre, and give each book the genre that its readers used most.
"""

# Genre -> the tags that indicate it
GENRE_TAGS = {
    "Fantasy": ["fantasy", "urban-fantasy", "epic-fantasy", "magic"],
    "Science Fiction": ["science-fiction", "sci-fi", "scifi", "sf"],
    "Romance": ["romance", "contemporary-romance", "historical-romance", "chick-lit"],
    "Mystery & Thriller": ["mystery", "crime", "thriller", "suspense"],
    "Horror": ["horror", "scary"],
    "Historical Fiction": ["historical-fiction", "historical"],
    "Young Adult": ["young-adult", "ya", "teen"],
    "Children's": ["childrens", "children", "kids", "picture-books", "middle-grade"],
    "Classics": ["classics", "classic", "classic-literature"],
    "Literary Fiction": ["literary-fiction", "literature", "contemporary-fiction"],
    "Comics & Manga": ["graphic-novels", "graphic-novel", "comics", "manga"],
    "Non-fiction": [
        "non-fiction",
        "nonfiction",
        "biography",
        "memoir",
        "history",
        "science",
        "self-help",
    ],
    "Religion": ["christian", "religion", "christianity", "spirituality"],
    "Poetry": ["poetry", "poems"],
}

# The genre of the books that have none of the tags above
NO_GENRE = "Other"


def tag_to_genre():
    """Return a dictionary tag -> genre, the inverse of ``GENRE_TAGS``."""
    mapping = {}
    for genre, tags in GENRE_TAGS.items():
        for tag in tags:
            mapping[tag] = genre
    return mapping


def assign_genres(book_tags):
    """
    Give each book the genre whose tags were used most by its readers.

    Parameters
    ----------
    book_tags : pandas.DataFrame
        One row per (book, tag), with the columns ``book_id``, ``tag_name``
        and ``count`` (the number of users who used the tag).

    Returns
    -------
    pandas.DataFrame
        One row per book: ``book_id`` and ``genre``.
    """
    votes = book_tags.assign(genre=book_tags["tag_name"].map(tag_to_genre()))
    votes = votes.dropna(subset=["genre"])
    votes = votes.groupby(["book_id", "genre"], as_index=False)["count"].sum()
    # Sort the votes of each book from the most used genre: keep the first one
    votes = votes.sort_values(["book_id", "count"], ascending=[True, False])
    return votes.drop_duplicates(subset="book_id")[["book_id", "genre"]]

#This function picks one genre for each book by letting the readers' 
# tags vote. Every time a user tagged a book with "fantasy" or "magic," 
# that's a vote for Fantasy. The genre with the most votes wins.