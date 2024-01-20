from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from rdflib import Graph, Namespace

# Define RDF file URL
rdf_file_url = "https://raw.githubusercontent.com/spacetelescope/mast_expand-vocab/main/vocabs/data-product-type.rdf"

# Load RDF file from URL
g = Graph()
g.parse(rdf_file_url, format="xml")

# Define SKOS namespace
skos = Namespace("http://www.w3.org/2004/02/skos/core#")

# Extract tags and synonyms from RDF
tags = []
synonyms = {}
descendants = {}

for s, p, o in g.triples((None, skos.prefLabel, None)):
    if isinstance(o, str):
        tag = str(o)
        tags.append(tag)
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

def main():
    while True:
        user_input = prompt('Start typing a tag: ', completer=CustomCompleter(), complete_while_typing=True)

        # Check for exit command
        if user_input.lower() == "exit":
            break

        print('You selected:', user_input)
        if len(descendants[user_input])>0:
            # Suggest descendants
            print('You may want to consider these more specific tags:')
            for i in descendants[user_input]:
                print(f'  - {i}')

if __name__ == '__main__':
    main()
