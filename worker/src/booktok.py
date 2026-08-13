"""Curated BookTok works verified against exact Open Library work identifiers."""

UPDATED = "2026-08-13"
SOURCES = [
    {"name": "TikTok 2026 Summer Reading List", "url": "https://newsroom.tiktok.com/the-booktok-communitys-2026-summer-reading-list?lang=en"},
    {"name": "Kobo: Best of BookTok 2026", "url": "https://www.kobo.com/blog/the-best-of-booktok-of-2026"},
]

# Featured order is editorial rather than a claim about sales or TikTok views.
WORKS = [
    ("OL42543873W", "Fantasy"), ("OL37575309W", "Romance"),
    ("OL16509148W", "Emotional reads"), ("OL17352669W", "Romantasy"),
    ("OL21745884W", "Science fiction"), ("OL42412330W", "Romance"),
    ("OL5735363W", "Fantasy"), ("OL16044142W", "Fantasy"),
    ("OL24726867W", "Science fiction"), ("OL59797W", "Science fiction"),
    ("OL16532075W", "Literary fiction"), ("OL25434351W", "Romance"),
    ("OL16014245W", "Romance"), ("OL28775218W", "Fantasy"),
    ("OL20853227W", "Emotional reads"), ("OL27850288W", "Romance"),
    ("OL24178205W", "Romance"), ("OL24390422W", "Romance"),
    ("OL27893158W", "Romantasy"), ("OL26758111W", "Emotional reads"),
    ("OL34774028W", "Romantasy"),
]

CATEGORIES = ["All", "Romance", "Romantasy", "Fantasy", "Science fiction", "Emotional reads", "Literary fiction"]
