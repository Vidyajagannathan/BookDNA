import re


SUBJECT_MAPPINGS = {
    "fantasy": ("Fantasy", "Genre", .9), "mythology": ("Mythology", "Knowledge", .95),
    "classics": ("Classics", "Genre", .9), "classic literature": ("Classics", "Genre", .9),
    "political": ("Political Intrigue", "Theme", .75), "dystopia": ("Dystopian", "Subgenre", .9),
    "philosophy": ("Philosophical", "Style", .85), "romance": ("Romance", "Genre", .85),
    "romantasy": ("Romantasy", "Subgenre", .9),
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
    "crime": ("Crime", "Genre", .85), "detective": ("Detective Fiction", "Subgenre", .8),
    "memoir": ("Memoir", "Genre", .9), "biography": ("Biography", "Genre", .85),
    "autobiography": ("Memoir", "Genre", .9), "poetry": ("Poetry", "Genre", .9),
    "young adult": ("Young Adult", "Audience", .8), "juvenile fiction": ("Children's", "Audience", .8),
    "children": ("Children's", "Audience", .75), "graphic novel": ("Graphic Novels", "Format", .9),
    "comics": ("Graphic Novels", "Format", .8), "humor": ("Humour", "Mood", .8),
    "humour": ("Humour", "Mood", .8), "satire": ("Satire", "Style", .85),
    "travel": ("Travel", "Knowledge", .8), "art": ("Art & Design", "Knowledge", .8),
    "design": ("Art & Design", "Knowledge", .75), "business": ("Business", "Knowledge", .8),
    "economics": ("Economics", "Knowledge", .85), "politics": ("Politics", "Knowledge", .85),
    "cookery": ("Food & Cooking", "Knowledge", .85), "cooking": ("Food & Cooking", "Knowledge", .85),
    "health": ("Health", "Knowledge", .75), "self help": ("Personal Growth", "Knowledge", .8),
    "true crime": ("True Crime", "Genre", .9), "nature": ("Nature", "Knowledge", .8),
    "environment": ("Environment", "Knowledge", .8), "technology": ("Technology", "Knowledge", .8),
}

SERIES_RULES = [
    {"id":"acotar","name":"A Court of Thorns and Roses","author":"sarah j maas","titles":["a court of thorns and roses","a court of mist and fury","a court of wings and ruin","a court of frost and starlight","a court of silver flames"],"traits":[("Fantasy","Genre",.9),("Romance","Genre",.85),("Romantasy","Subgenre",.9),("Adventure","Mood",.75)]},
    {"id":"throne-of-glass","name":"Throne of Glass","author":"sarah j maas","titles":["the assassin s blade","throne of glass","crown of midnight","heir of fire","queen of shadows","empire of storms","tower of dawn","kingdom of ash"],"traits":[("Fantasy","Genre",.9),("Adventure","Mood",.85),("Romance","Genre",.7)]},
    {"id":"crescent-city","name":"Crescent City","author":"sarah j maas","titles":["house of earth and blood","house of sky and breath","house of flame and shadow"],"traits":[("Fantasy","Genre",.9),("Romance","Genre",.8),("Mystery","Genre",.7)]},
    {"id":"caraval","name":"Caraval","author":"stephanie garber","titles":["caraval","legendary","finale","spectacular"],"traits":[("Fantasy","Genre",.9),("Romance","Genre",.75),("Adventure","Mood",.8)]},
    {"id":"once-upon-a-broken-heart","name":"Once Upon a Broken Heart","author":"stephanie garber","titles":["once upon a broken heart","the ballad of never after","a curse for true love","the mirror of infinite endings"],"traits":[("Fantasy","Genre",.9),("Romance","Genre",.85),("Adventure","Mood",.7)]},
    {"id":"inheritance-games","name":"The Inheritance Games","author":"jennifer lynn barnes","titles":["the inheritance games","the hawthorne legacy","the final gambit","the brothers hawthorne","the grandest game","games untold","glorious rivals","the same backward as forward"],"traits":[("Mystery","Genre",.9),("Thriller","Genre",.8),("Romance","Genre",.65)]},
]


def _trait(name: str, category: str, weight: float) -> dict:
    return {"id": name.lower().replace(" ", "-"), "name": name, "category": category, "weight": weight}


def _normalise(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", str(value).lower()).split())


def _series_match(title: str, author: str, raw_title: str):
    for rule in SERIES_RULES:
        if rule["author"] not in author:
            continue
        matched=[candidate for candidate in rule["titles"] if candidate in title]
        if matched:
            collection_syntax="/" in raw_title or ";" in raw_title or any(marker in title for marker in ("box set","boxed set","collection","omnibus","bundle"))
            if not collection_syntax:
                starts=[candidate for candidate in matched if title.startswith(candidate)]
                matched=[max(starts,key=len)] if starts else [max(matched,key=len)]
            return rule, matched
    return None, []


def map_subjects(subjects: list[str]) -> list[dict]:
    found = {}
    for subject in subjects[:30]:
        normalized = _normalise(subject)
        for needle, (name, category, weight) in SUBJECT_MAPPINGS.items():
            if needle == "science" and "science fiction" in normalized:
                continue
            if re.search(rf"(?:^| )({re.escape(needle)})(?:s)?(?: |$)", normalized):
                found[name] = _trait(name, category, max(weight, found.get(name, {}).get("weight", 0)))
    return list(found.values())


def classify_book(book: dict) -> dict:
    """Classify a book transparently, falling back to conservative title/author rules."""
    subjects = [str(value) for value in (book.get("subjects") or []) if value]
    traits = map_subjects(subjects)
    source = "subjects" if traits else "none"
    raw_title=str(book.get("title", "")); title = _normalise(raw_title)
    author = _normalise(book.get("author", ""))
    text = f"{title} {author}"
    fallback = []
    series, matched_titles = _series_match(title,author,raw_title)

    if series and not traits:
        fallback=[_trait(*trait) for trait in series["traits"]]
        traits,source=fallback,"verified_series"

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
    collection_markers=("box set","boxed set","collection","omnibus","ebook bundle","book bundle")
    is_collection=len(matched_titles)>1 or any(marker in title for marker in collection_markers)
    return {"traits":traits,"source":source,"reading_type":reading_type,"format_type":"collection" if is_collection else "single","series_id":series["id"] if series else None,"series_name":series["name"] if series else None,"matched_titles":matched_titles}


def plan_library_classifications(items: list[dict]) -> dict:
    """Plan collection coverage so omnibus and individual entries cannot double count."""
    records=[(item,classify_book(item["book"])) for item in items]
    individual_titles=set()
    for item,classification in records:
        if item["status"] in ("READ","CURRENTLY_READING") and classification["series_id"] and classification["format_type"]=="single":
            individual_titles.update((classification["series_id"],title) for title in classification["matched_titles"])
    plans={}
    for item,classification in records:
        matched=classification["matched_titles"]
        duplicates=[title for title in matched if (classification["series_id"],title) in individual_titles] if classification["format_type"]=="collection" else []
        counted=[title for title in matched if title not in duplicates]
        coverage=len(counted)/len(matched) if matched else 1
        state="included"
        if not classification["traits"]: state="needs_classification"
        elif classification["format_type"]=="collection" and duplicates: state="partial_collection" if counted else "duplicate_excluded"
        plans[item["book_id"]]={"classification":classification,"state":state,"counted_titles":counted,"duplicate_titles":duplicates,"coverage":coverage}
    return plans
