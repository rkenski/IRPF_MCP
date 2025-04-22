import xml.etree.ElementTree as ET
from collections import defaultdict
import sys

def infer_type(value):
    try:
        int(value)
        return "int"
    except ValueError:
        pass
    try:
        float(value)
        return "float"
    except ValueError:
        pass
    if value.lower() in ["true", "false"]:
        return "bool"
    return "string"

def analyze_element(element, path="", schema=None):
    if schema is None:
        schema = defaultdict(dict)

    tag_path = f"{path}/{element.tag}" if path else element.tag

    # Initialize if not already
    if tag_path not in schema:
        schema[tag_path] = {"attributes": {}, "children": set(), "text_type": set()}

    # Attributes
    for attr, val in element.attrib.items():
        attr_type = infer_type(val)
        schema[tag_path]["attributes"][attr] = attr_type

    # Text content
    if element.text and element.text.strip():
        text_type = infer_type(element.text.strip())
        schema[tag_path]["text_type"].add(text_type)

    # Children
    for child in element:
        schema[tag_path]["children"].add(child.tag)
        analyze_element(child, tag_path, schema)

    return schema

def format_schema(schema):
    lines = []
    for path in sorted(schema):
        entry = schema[path]
        lines.append(f"Element: {path}")
        if entry["attributes"]:
            lines.append("  Attributes:")
            for attr, attr_type in entry["attributes"].items():
                lines.append(f"    - {attr}: {attr_type}")
        if entry["text_type"]:
            lines.append(f"  Text content types: {', '.join(entry['text_type'])}")
        if entry["children"]:
            lines.append("  Children:")
            for child in sorted(entry["children"]):
                lines.append(f"    - {child}")
        lines.append("")  # Empty line for separation
    return "\n".join(lines)

def extract_schema(xml_file, output_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    schema = analyze_element(root)
    formatted_schema = format_schema(schema)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(formatted_schema)

    print(f"Schema written to {output_file}")
    return formatted_schema

# Example usage:
# python xml_schema_extractor.py input.xml schema.txt

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python xml_schema_extractor.py input.xml output.txt")
    else:
        extract_schema(sys.argv[1], sys.argv[2])


file = '/home/kenski/ProgramasRFB/IRPF2025/aplicacao/dados/30390505838/30390505838-0000000000.xml'
result = extract_schema(file, 'schema.txt')





