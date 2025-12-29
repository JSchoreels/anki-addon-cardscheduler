import xml.etree.ElementTree as ET


def katakana_to_hiragana(text):
    result = ""
    for char in text:
        if 'ァ' <= char <= 'ヶ':
            result += chr(ord(char) - ord('ァ') + ord('ぁ'))
        else:
            result += char
    return result


def process_reading(text):
    # Remove any suffixes starting from a dot and remove dashes as in the original script.
    if text:
        text = text.replace('-', '')
    return text


def apply_rendaku(reading):
    """Convert a reading to its rendaku (voiced) form if applicable.

    Returns the rendaku version, or None if no rendaku applies.
    """
    if not reading:
        return None

    # Rendaku mappings
    rendaku_map = {
        'か': 'が', 'き': 'ぎ', 'く': 'ぐ', 'け': 'げ', 'こ': 'ご',
        'さ': 'ざ', 'し': 'じ', 'す': 'ず', 'せ': 'ぜ', 'そ': 'ぞ',
        'た': 'だ', 'ち': 'ぢ', 'つ': 'づ', 'て': 'で', 'と': 'ど',
        'は': 'ば', 'ひ': 'び', 'ふ': 'ぶ', 'へ': 'べ', 'ほ': 'ぼ',
    }

    first_char = reading[0]
    if first_char in rendaku_map:
        return rendaku_map[first_char] + reading[1:]

    return None


def filter_rendaku_readings(readings):
    """Filter out rendaku versions when the non-rendaku version exists.

    For example, if both 'とき' and 'どき' exist, remove 'どき'.
    """
    readings_set = set(readings)
    filtered = set()

    for reading in readings:
        # Check if this reading has a non-rendaku version
        rendaku_version = apply_rendaku(reading)

        # If this IS the rendaku version of another reading that exists, skip it
        is_rendaku = False
        for other_reading in readings_set:
            if other_reading != reading and apply_rendaku(other_reading) == reading:
                # This reading is the rendaku version of other_reading
                is_rendaku = True
                break

        if not is_rendaku:
            filtered.add(reading)

    return filtered


def transform_kanjidic(input_file, output_file):
    tree = ET.parse(input_file)
    root = tree.getroot()

    # Create new root for light version
    light_root = ET.Element("kanjidic_light")

    for character in root.findall('character'):
        literal_elem = character.find('literal')
        if literal_elem is None:
            continue

        # Create a new character element
        char_el = ET.SubElement(light_root, "character")
        literal = ET.SubElement(char_el, "literal")
        literal.text = literal_elem.text

        # Collect all readings first, then filter
        ja_kun_readings = []
        ja_on_readings = []

        # Look for readings in reading_meaning/rmgroup
        readings_root = character.find("reading_meaning")
        if readings_root is not None:
            for rmgroup in readings_root.findall("rmgroup"):
                # ja_kun readings
                for reading in rmgroup.findall("reading[@r_type='ja_kun']"):
                    processed = process_reading(reading.text)
                    if processed:
                        ja_kun_readings.append(processed)
                # ja_on readings (convert to hiragana)
                for reading in rmgroup.findall("reading[@r_type='ja_on']"):
                    processed = process_reading(reading.text)
                    if processed:
                        ja_on_readings.append(katakana_to_hiragana(processed))

        # Filter out rendaku versions (only for kun-yomi, not on-yomi)
        ja_kun_readings = filter_rendaku_readings(ja_kun_readings)
        ja_on_readings = filter_rendaku_readings(ja_on_readings)
        # Don't filter on-yomi - both たい and だい are valid readings, not rendaku

        # Add filtered readings to XML
        for reading in ja_kun_readings:
            r_elem = ET.SubElement(char_el, "ja_kun")
            r_elem.text = reading
        for reading in ja_on_readings:
            r_elem = ET.SubElement(char_el, "ja_on")
            r_elem.text = reading

    # Write out the new light XML file with pretty formatting
    tree_light = ET.ElementTree(light_root)
    ET.indent(tree_light, space="\t", level=0)  # Pretty print for Python 3.9+
    tree_light.write(output_file, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    input_file = "cardscheduler/resources/kanjidic2.xml"
    output_file = "cardscheduler/resources/kanjidic2_light.xml"
    transform_kanjidic(input_file, output_file)
    print(f"Light version written to {output_file}")