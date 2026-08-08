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
}

def map_subjects(subjects: list[str]) -> list[dict]:
    found = {}
    for subject in subjects[:30]:
        normalized = re.sub(r"[^a-z ]", "", subject.lower())
        for needle, (name, category, weight) in SUBJECT_MAPPINGS.items():
            if needle in normalized:
                found[name] = {"id": name.lower().replace(" ", "-"), "name": name, "category": category, "weight": max(weight, found.get(name, {}).get("weight", 0))}
    return list(found.values())

