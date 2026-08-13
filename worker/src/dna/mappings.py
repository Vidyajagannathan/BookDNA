import re


SUBJECT_MAPPINGS = {
    "fantasy": ("Fantasy", "Genre", .9), "mythology": ("Mythology", "Knowledge", .95),
    "classics": ("Classics", "Genre", .9), "classic literature": ("Classics", "Genre", .9),
    "political": ("Political Intrigue", "Theme", .75), "dystopia": ("Dystopian", "Subgenre", .9),
    "philosophy": ("Philosophical", "Style", .85), "romance": ("Romance", "Genre", .85),
    "thriller": ("Thriller", "Genre", .9), "mystery": ("Mystery", "Genre", .9),
    "science fiction": ("Science Fiction", "Genre", .9), "historical": ("Historical Fiction", "Genre", .8),
    "horror": ("Horror", "Genre", .9), "gothic": ("Gothic", "Subgenre", .85),
    "war": ("War", "Theme", .75), "family": ("Family", "Theme", .7),
    "friendship": ("Friendship", "Theme", .75), "adventure": ("Adventure", "Mood", .75),
    "psychology": ("Psychology", "Knowledge", .85), "history": ("History", "Knowledge", .85),
    "religion": ("Religion", "Knowledge", .85), "spirituality": ("Spirituality", "Knowledge", .85),
    "sacred book": ("Sacred Texts", "Knowledge", .9), "sacred text": ("Sacred Texts", "Knowledge", .9),
    "hindu philosophy": ("Hindu Philosophy", "Knowledge", .95), "hinduism": ("Hindu Philosophy", "Knowledge", .9),
    "education": ("Education", "Knowledge", .8), "science": ("Science", "Knowledge", .85),
    "hindi literature": ("Hindi Literature", "Literature", .9), "hindi language": ("Language Learning", "Knowledge", .8),
    "language learning": ("Language Learning", "Knowledge", .8), "school textbook": ("School Textbook", "Reading Context", .8),
}


def _trait(name: str, category: str, weight: float) -> dict:
    return {"id": name.lower().replace(" ", "-"), "name": name, "category": category, "weight": weight}


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", str(value).lower()).strip()


def map_subjects(subjects: list[str]) -> list[dict]:
    found = {}
    for subject in subjects[:30]:
        normalized = _normalise(subject)
        for needle, (name, category, weight) in SUBJECT_MAPPINGS.items():
            if needle == "science" and "science fiction" in normalized:
                continue
            if needle in normalized:
                found[name] = _trait(name, category, max(weight, found.get(name, {}).get("weight", 0)))
    return list(found.values())


def classify_book(book: dict) -> dict:
    """Classify a book transparently, falling back to conservative title/author rules."""
    subjects = [str(value) for value in (book.get("subjects") or []) if value]
    traits = map_subjects(subjects)
    source = "subjects" if traits else "none"
    title = _normalise(book.get("title", ""))
    author = _normalise(book.get("author", ""))
    text = f"{title} {author}"
    fallback = []

    if not traits:
        if "bhagavad gita" in text or "bhagavadgita" in text or "bagavath gita" in text:
            fallback = [_trait("Hindu Philosophy", "Knowledge", .95), _trait("Sacred Texts", "Knowledge", .9), _trait("Spirituality", "Knowledge", .85)]
        elif "subconscious mind" in title and "murphy" in author:
            fallback = [_trait("Psychology", "Knowledge", .85)]
        elif ("science textbook" in title or "textbook for class x" in title) and ("ncert" in text or "class x" in title):
            fallback = [_trait("Science", "Knowledge", .85), _trait("Education", "Knowledge", .8), _trait("School Textbook", "Reading Context", .8)]
        elif ("vasant" in title or "hindi" in title) and ("ncert" in text or "class 7" in title or "part 2" in title):
            fallback = [_trait("Hindi Literature", "Literature", .9), _trait("Language Learning", "Knowledge", .8), _trait("Education", "Knowledge", .8), _trait("School Textbook", "Reading Context", .8)]
        if fallback:
            traits, source = fallback, "title_author_fallback"

    academic_markers = ("textbook", "ncert", "class x", "class 7", "school textbook")
    reading_type = "academic" if any(marker in text or any(marker in _normalise(subject) for subject in subjects) for marker in academic_markers) else "recreational"
    return {"traits": traits, "source": source, "reading_type": reading_type}
