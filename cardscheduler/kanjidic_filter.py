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
        text = text.split('.')[0]
        text = text.replace('-', '')
    return text


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

        # Look for readings in reading_meaning/rmgroup
        readings_root = character.find("reading_meaning")
        if readings_root is not None:
            for rmgroup in readings_root.findall("rmgroup"):
                # ja_kun readings
                for reading in rmgroup.findall("reading[@r_type='ja_kun']"):
                    processed = process_reading(reading.text)
                    if processed:
                        r_elem = ET.SubElement(char_el, "ja_kun")
                        r_elem.text = processed
                # ja_on readings (convert to hiragana)
                for reading in rmgroup.findall("reading[@r_type='ja_on']"):
                    processed = process_reading(reading.text)
                    if processed:
                        r_elem = ET.SubElement(char_el, "ja_on")
                        r_elem.text = katakana_to_hiragana(processed)

    # Write out the new light XML file with pretty formatting
    tree_light = ET.ElementTree(light_root)
    ET.indent(tree_light, space="\t", level=0)  # Pretty print for Python 3.9+
    tree_light.write(output_file, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    input_file = "cardscheduler/kanjidic2.xml"
    output_file = "cardscheduler/kanjidic2_light.xml"
    transform_kanjidic(input_file, output_file)
    print(f"Light version written to {output_file}")