"""
Keyword Synonym System
Maps keywords to their synonyms for better matching
"""

# Keyword synonym mapping
# Format: primary_keyword -> [list of synonyms]
KEYWORD_SYNONYMS = {
    # Carbon Capture
    "co2 capture": ["carbon dioxide capture", "carbon capture", "co₂ capture", "ccs"],
    "carbon capture and storage": ["ccs", "carbon capture storage", "carbon sequestration"],
    "direct air capture": ["dac", "air capture", "atmospheric co2 removal"],
    "calcium looping": ["cal", "calcium carbonate looping", "caco3 looping"],
    "carbon neutrality": ["carbon neutral", "net zero", "carbon-neutral", "decarbonization", "decarbonisation"],

    # Process Engineering
    "techno-economic analysis": ["tea", "economic analysis", "technoeconomic", "cost analysis", "economic assessment"],
    "process modeling": ["process modelling", "process simulation", "mathematical modeling", "process model"],
    "process simulation": ["simulation", "process modelling", "dynamic simulation"],
    "process optimization": ["optimization", "optimisation", "process improvement"],
    "system integration": ["integration", "system design", "integrated system"],

    # Energy
    "renewable energy": ["clean energy", "sustainable energy", "green energy", "renewables"],
    "energy system optimization": ["energy optimization", "energy system", "optimal energy"],
    "power plant": ["power station", "power generation", "electricity generation"],

    # AI/Data
    "ai-based optimization": ["ai optimization", "artificial intelligence", "machine learning optimization", "ml optimization"],
    "data-driven modeling": ["data-driven model", "data-based modeling", "machine learning model"],
    "ai based modeling": ["ai modeling", "ai model", "machine learning modeling", "ml model"],

    # Fuels
    "hydrogen": ["h2", "hydrogen production", "hydrogen energy", "green hydrogen"],
    "ammonia": ["nh3", "ammonia production", "green ammonia", "ammonia synthesis"],

    # Software/Tools
    "aspen": ["aspen plus", "aspen hysys", "aspentech"],

    # Pollutants
    "co2": ["carbon dioxide", "co₂", "carbon-dioxide"],
    "nox": ["nitrogen oxide", "nitrogen oxides", "no2", "no", "nitric oxide"],

    # Analysis Methods
    "lca": ["life cycle assessment", "lifecycle assessment", "life-cycle analysis", "environmental impact assessment"],
}

# Exclusion keywords - papers containing these will be filtered out
EXCLUSION_KEYWORDS = [
    # Catalysis terms
    "catalyst", "catalysts", "catalysis", "catalytic", "catalyzed",
    "photocatalyst", "electrocatalyst", "biocatalyst",
    "catalytic conversion", "catalytic reaction", "catalytic activity",
    "catalytic performance", "catalyst support",

    # Metal catalysts (precious metals)
    "platinum", "pt catalyst", "palladium", "pd catalyst",
    "rhodium", "rh catalyst", "ruthenium", "ru catalyst",
    "iridium", "ir catalyst", "gold catalyst", "au catalyst",
    "silver catalyst", "ag catalyst",

    # Common metal catalysts
    "nickel catalyst", "ni catalyst", "copper catalyst", "cu catalyst",
    "iron catalyst", "fe catalyst", "cobalt catalyst", "co catalyst",
    "zinc catalyst", "zn catalyst", "molybdenum catalyst", "mo catalyst",

    # Metal-specific research (too specific for process engineering)
    "metal nanoparticle", "metal oxide catalyst", "bimetallic catalyst",
    "metal organic framework catalyst", "mof catalyst",
    "zeolite catalyst", "heterogeneous catalyst",
]

# Build reverse mapping for faster lookup
SYNONYM_TO_PRIMARY = {}
for primary, synonyms in KEYWORD_SYNONYMS.items():
    SYNONYM_TO_PRIMARY[primary] = primary
    for synonym in synonyms:
        SYNONYM_TO_PRIMARY[synonym.lower()] = primary


def expand_keywords(keywords: list) -> set:
    """
    Expand a list of keywords to include all their synonyms

    Args:
        keywords: List of keywords

    Returns:
        Set of keywords including all synonyms
    """
    expanded = set()

    for keyword in keywords:
        keyword_lower = keyword.strip().lower()
        expanded.add(keyword_lower)

        # Check if this keyword has synonyms
        if keyword_lower in KEYWORD_SYNONYMS:
            expanded.update(syn.lower() for syn in KEYWORD_SYNONYMS[keyword_lower])

        # Check if this is a synonym of another keyword
        if keyword_lower in SYNONYM_TO_PRIMARY:
            primary = SYNONYM_TO_PRIMARY[keyword_lower]
            expanded.add(primary)
            if primary in KEYWORD_SYNONYMS:
                expanded.update(syn.lower() for syn in KEYWORD_SYNONYMS[primary])

    return expanded


def match_keywords_in_text(text: str, keywords: list) -> dict:
    """
    Match keywords (including synonyms) in text

    Args:
        text: Text to search in
        keywords: List of keywords to search for

    Returns:
        Dict with matched_keywords (set), match_count (int), matched_terms (list of tuples)
    """
    text_lower = text.lower()

    # Expand keywords to include synonyms
    expanded_keywords = expand_keywords(keywords)

    matched_keywords = set()
    matched_terms = []  # (original_keyword, matched_synonym)

    for keyword in keywords:
        keyword_lower = keyword.strip().lower()

        # Get all possible forms of this keyword
        possible_forms = {keyword_lower}
        if keyword_lower in KEYWORD_SYNONYMS:
            possible_forms.update(syn.lower() for syn in KEYWORD_SYNONYMS[keyword_lower])

        # Check if any form matches
        for form in possible_forms:
            if form in text_lower:
                matched_keywords.add(keyword_lower)
                matched_terms.append((keyword, form))
                break

    return {
        'matched_keywords': matched_keywords,
        'match_count': len(matched_keywords),
        'matched_terms': matched_terms,
        'total_keywords': len(keywords)
    }


def get_keyword_variations(keyword: str) -> list:
    """
    Get all variations (synonyms) of a keyword

    Args:
        keyword: Keyword to get variations for

    Returns:
        List of all variations including the original
    """
    keyword_lower = keyword.strip().lower()
    variations = {keyword_lower}

    if keyword_lower in KEYWORD_SYNONYMS:
        variations.update(syn.lower() for syn in KEYWORD_SYNONYMS[keyword_lower])

    if keyword_lower in SYNONYM_TO_PRIMARY:
        primary = SYNONYM_TO_PRIMARY[keyword_lower]
        variations.add(primary)
        if primary in KEYWORD_SYNONYMS:
            variations.update(syn.lower() for syn in KEYWORD_SYNONYMS[primary])

    return list(variations)


def should_exclude_paper(text: str) -> tuple[bool, list]:
    """
    Check if paper should be excluded based on exclusion keywords

    Args:
        text: Text to check (title + abstract)

    Returns:
        Tuple of (should_exclude: bool, matched_exclusion_keywords: list)
    """
    text_lower = text.lower()
    matched_exclusions = []

    for exclusion_keyword in EXCLUSION_KEYWORDS:
        if exclusion_keyword in text_lower:
            matched_exclusions.append(exclusion_keyword)

    # Exclude if any exclusion keyword is found
    should_exclude = len(matched_exclusions) > 0

    return should_exclude, matched_exclusions


# Example usage
if __name__ == "__main__":
    # Test synonym expansion
    test_keywords = ["CO2", "Hydrogen", "LCA"]

    print("Original keywords:", test_keywords)
    print()

    expanded = expand_keywords(test_keywords)
    print("Expanded keywords:")
    for kw in sorted(expanded):
        print(f"  - {kw}")
    print()

    # Test text matching
    test_text = """
    This study presents a comprehensive life cycle assessment of green hydrogen production
    using renewable energy sources. The carbon dioxide emissions were reduced by 80%
    compared to conventional methods.
    """

    result = match_keywords_in_text(test_text, test_keywords)
    print(f"Matched {result['match_count']} out of {result['total_keywords']} keywords:")
    for original, matched in result['matched_terms']:
        print(f"  - '{original}' matched via '{matched}'")
