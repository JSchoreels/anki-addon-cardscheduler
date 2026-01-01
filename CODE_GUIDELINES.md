# Code Style Guidelines

## Python Best Practices

### 1. Use List Comprehensions
Prefer list comprehensions over explicit loops when building lists:

```python
# Good
meanings = [meaning.text for meaning in character.findall('meaning') if meaning.text]

# Avoid
meanings = []
for meaning in character.findall('meaning'):
    if meaning.text:
        meanings.append(meaning.text)
```

### 2. Avoid Obvious Comments
Only add comments when the code logic isn't self-evident:

```python
# Good
meanings = [meaning.text for meaning in character.findall('meaning') if meaning.text]

# Avoid - comment is obvious
# Get meanings
meanings = [meaning.text for meaning in character.findall('meaning') if meaning.text]
```

### 3. Extract Common Code
Don't repeat exception handling or common patterns - extract into helper functions:

```python
# Good - shared helper
def _load_kanjidic_xml():
    """Load kanjidic2_light.xml and return the root element, or None on error."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    xml_file = os.path.join(current_dir, 'resources', 'kanjidic2_light.xml')

    try:
        tree = ET.parse(xml_file)
        return tree.getroot()
    except Exception as e:
        print(f"Unexpected error loading kanji data: {e}")
        showInfo(f"Error loading kanji data: {str(e)}")
        return None

# Both functions use the helper
def load_kanji_meanings():
    root = _load_kanjidic_xml()
    if root is None:
        return {}
    # ...

def load_kanji_dictionnary_readings():
    root = _load_kanjidic_xml()
    if root is None:
        return {}
    # ...
```

### 4. Don't Limit Data at Source
Keep all data in intermediate representations, only limit when displaying:

```python
# Good - keep all meanings in XML
for meaning in meanings:
    m_elem = ET.SubElement(char_el, "meaning")
    m_elem.text = meaning

# Later, limit when displaying
meanings_text = ', '.join(meanings[:3])

# Avoid - limiting too early
for meaning in meanings[:3]:  # Don't limit here
    m_elem = ET.SubElement(char_el, "meaning")
    m_elem.text = meaning
```

## Architecture Principles

### Separation of Concerns
- **Data Layer**: Collect and store structured data (lists, dictionaries, objects)
- **Presentation Layer**: Convert data structures into HTML/formatted output
- **Storage Layer**: Persist to database/files

Example:
```python
# scheduler.py - Data layer
card_info.related_cards_known = [(card, shared_kanji), ...]  # Data structure

# html_formatter.py - Presentation layer
html = format_card_html(card_info, meanings, readings)  # Generate HTML

# anki_interface.py - Storage layer
note.fields[field_index] = html  # Store in Anki
```

### Keep Logic in the Right Place
- **scheduler.py**: Scheduling algorithms, scoring, related word logic
- **html_formatter.py**: HTML generation, color assignment, styling
- **dictionary.py**: Dictionary loading and data access
- **word_parser.py**: Text parsing, kanji/reading extraction
