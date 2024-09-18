from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from rdflib import Graph, Namespace
import csv
import os
import re

# TO-DO:
# ---Handling of multiple vocabularies
# ---Refactor code

# Define RDF file URL
rdf_file_url = "https://raw.githubusercontent.com/spacetelescope/mast_expand-vocab/main/vocabs/data-product-type.rdf"

# Load RDF file from URL
g = Graph()
g.parse(rdf_file_url, format="xml")

# Define SKOS namespace
skos = Namespace("http://www.w3.org/2004/02/skos/core#")

# Initialize lists and dictionaries
tags = []  # list of tags
synonyms = {}  # dictionary mapping tags to their altLabels and hiddenLabels
descendants = {}  # dictionary mapping tags to their descendants
uri = {}  # dictionary mapping tag prefLabels to their URIs

# Extract tags and synonyms from RDF
print('Loading vocabulary...')
for s, p, o in g.triples((None, skos.prefLabel, None)):
    if isinstance(o, str):
        tag = str(o)
        tags.append(tag)
        uri[tag] = str(s)
        synonyms[tag] = []

        # Populate descendants
        q = f"""
            SELECT ?descendantPrefLabel (COUNT(?nestedDescendant) as ?descendantCount)
            WHERE {{
                ?x rdf:type skos:Concept .
                ?x skos:prefLabel ?prefLabel .
                ?x ^skos:broader+ ?descendant .
                ?descendant skos:prefLabel ?descendantPrefLabel .
                OPTIONAL {{
                  ?descendant ^skos:broader+ ?nestedDescendant .
                }}
                FILTER (?prefLabel = "{tag}"@en) .
            }}
            GROUP BY ?descendant
            ORDER BY DESC(?descendantCount)
        """
        descendants[tag] = [str(r["descendantPrefLabel"]) for r in g.query(q)]

    # Populate synonyms from altLabels
    for alt_label_s, alt_label_p, alt_label_o in g.triples((s, skos.altLabel, None)):
        if isinstance(alt_label_o, str):
            synonym = str(alt_label_o)
            synonyms[tag].append(synonym)

    # Populate synonyms from hiddenLabels
    for hidden_label_s, hidden_label_p, hidden_label_o in g.triples((s, skos.hiddenLabel, None)):
        if isinstance(hidden_label_o, str):
            synonym = str(hidden_label_o)
            synonyms[tag].append(synonym)

# Sort tags by descendant count, so that higher-level tags come first in the loop
tags.sort(key=lambda tag: len(descendants.get(tag, [])), reverse=True)

# Print statements for debugging.
# print("tags:", tags)
# print("Synonyms:", synonyms)
# print("Descendants:", descendants)


class CustomCompleter(Completer):
    def get_completions(self, document, complete_event):
        input_text = document.text_before_cursor
        words = input_text.split()

        completions_added = set()

        # Check if the current word is already a complete tag
        for tag in tags:
            if (input_text.lower() == tag.lower()) and input_text not in completions_added:
                yield Completion(tag, start_position=0)
                completions_added.add(tag)

        # Suggest tags that contain all the input space-separated strings.
        # First loop is to prioritize tags that start one of the space-separated strings.
        for tag in tags:
            for word in words:
                if tag.lower().startswith(word) and all(x.lower() in tag.lower() for x in words) and tag not in completions_added:
                    yield Completion(tag, start_position=-len(input_text))
                    completions_added.add(tag)
        for tag in tags:
            if tag not in completions_added and all(x.lower() in tag.lower() for x in words):
                yield Completion(tag, start_position=-len(input_text))
                completions_added.add(tag)

        # Add synonyms to suggestions, but make them a different color.
        for tag, syn_list in synonyms.items():
            for synonym in syn_list:
                for word in words:
                    if tag not in completions_added and synonym.lower().startswith(word) and all(x.lower() in synonym.lower() for x in words):
                        yield Completion(tag, start_position=-len(input_text), style='fg:#0000FF bold')
                        completions_added.add(tag)
        for tag, syn_list in synonyms.items():
            for synonym in syn_list:
                if tag not in completions_added and all(x.lower() in synonym.lower() for x in words):
                    yield Completion(tag, start_position=-len(input_text), style='fg:#0000FF bold')
                    completions_added.add(tag)


def select_concepts() -> list:

    assigned_concepts = []
    while True:
        user_input = prompt('Start typing a tag: ', completer=CustomCompleter(), complete_while_typing=True)

        # Check for exit command
        if user_input.lower() in ("done", "exit", "quit"):
            break

        assigned_concepts.append(user_input)

        print('You selected:', user_input)
        if len(descendants[user_input]) > 0:
            # Suggest descendants
            print('which has these descendants:')
            for i in descendants[user_input]:
                print(f'  - {i}')

        print('Enter another tag, or type DONE to finish tagging this suffix.extension combination.')

    return assigned_concepts


def create_mapping_file(output_path) -> list:
    output_columns = ['suffix', 'extension', 'tag']
    with open(output_path, 'w', newline='') as output_file:
        csv_writer = csv.DictWriter(output_file, fieldnames=output_columns)
        csv_writer.writeheader()
    return output_columns


def append_mapping_file(output_path, output_columns, suffix_extension, assigned_concepts) -> None:
    with open(output_path, 'a', newline='') as output_file:
        for k in assigned_concepts:
            csv_writer = csv.DictWriter(output_file, fieldnames=output_columns)
            csv_writer.writerow({
                output_columns[0]: suffix_extension.split('.', 1)[0].lower(),
                output_columns[1]: suffix_extension.split('.', 1)[1].lower(),
                output_columns[2]: uri[k]
            })
    print('Tag assignments for ' + suffix_extension + ' have been appended to the mapping file' + output_path + '.')


def find_suffix_extensions(directory) -> list:
    unique_suffix_extensions = set()

    pattern = re.compile(r'_([^_]*)(\.[\w.]+)$')

    for _, _, files in os.walk(directory):
        for file in files:
            match = pattern.search(file)
            if match:
                suffix_extension = match.group(1) + match.group(2)
                unique_suffix_extensions.add(suffix_extension)

    return list(unique_suffix_extensions)


def main() -> None:
    mapping_file = 'test.csv'
    output_columns = create_mapping_file(mapping_file)
    directory = '.'

    print('Found the following suffix.extension pairs in your working directory:')
    i = 0
    found_suffix_extensions = []
    for found_suffix_extension in find_suffix_extensions(directory):
        found_suffix = found_suffix_extension.split('.', 1)[0]
        found_extension = found_suffix_extension.split('.', 1)[1]
        print(str(i) + '. ' + found_suffix + '.' + found_extension)
        i += 1
        found_suffix_extensions.append(found_suffix_extension)

    while True:
        suffix_extension = prompt(f'Enter a filename suffix.extension '
                                  f'(e.g., {found_suffix}.{found_extension}), '
                                  f'\n or select one of the suffix.extensions '
                                  f'found above by entering the appropriate '
                                  f'integer (e.g., 0), \n or enter DONE to exit'
                                  f' the program: ')
        if suffix_extension.lower() in ("done", "exit", "quit"):
            break
        elif suffix_extension.isdigit():
            if int(suffix_extension) > len(found_suffix_extensions) - 1:
                print('You selected an out-of-range integer.')
                print('Please try again.')
                continue
            suffix_extension = found_suffix_extensions[int(suffix_extension)]
        elif '.' not in suffix_extension or '_' in suffix_extension:
            print('Format should be like: spec-cube.fits')
            print('Please try again.')
            continue
        else:
            pass

        assigned_concepts = select_concepts()
        append_mapping_file(mapping_file, output_columns, suffix_extension, assigned_concepts)


if __name__ == '__main__':
    main()
