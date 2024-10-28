from rdflib import Graph, Namespace
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import threading
import time

app = Flask(__name__)
CORS(app)

# Define RDF file URL
rdf_file_url = "https://raw.githubusercontent.com/spacetelescope/mast_expand-vocab/main/vocabs/data-product-type.rdf"

# Load RDF file from URL
g = Graph()
g.parse(rdf_file_url, format="xml")

# Define SKOS namespace
skos = Namespace("http://www.w3.org/2004/02/skos/core#")

# Initialize global variables to hold tags, URIs, synonyms, and descendants
tags: list[str] = []  # the list of human-readable tags
synonyms: dict[str, list[str]] = {}  # maps human-readable tags to synonym lists
descendants: dict[str, list[str]] = {}  # maps human-readable tags to descendant lists
uris: dict[str, str] = {}  # maps human-readable tags to their short URIs

# Extract tags and synonyms from RDF
for s, p, o in g.triples((None, skos.prefLabel, None)):
    if isinstance(o, str):
        tag = str(o)
        tags.append(tag)
        uris[tag] = str(s).split('#')[1]  # get short URI
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
        descendants[tag] = [str(r["descendantPrefLabel"]) for r in g.query(q)]  # type: ignore

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


# API to retrieve autocomplete suggestions with synonym support
@app.route('/autocomplete', methods=['GET'])
def get_completions() -> Response:
    input_text = request.args.get('q', '')  # Text input by user
    words = input_text.split()  # Split input text into words

    completions_added: list[str] = []  # Initialize list of typeahead suggestions

    # Check if the current input text is already a complete tag, and if so add it first.
    for tag in tags:
        if (input_text.lower() == tag.lower()) and input_text not in completions_added:
            completions_added.append(tag)

    # Then suggest tags that contain all the input space-separated strings.
    # First loop is to prioritize tags that start with one of the space-separated strings...
    for tag in tags:
        for word in words:
            if tag.lower().startswith(word) and all(x.lower() in tag.lower() for x in words) and tag not in completions_added:
                completions_added.append(tag)
    # ...second loop is for tags that don't start with one of the space-separated strings.
    for tag in tags:
        if tag not in completions_added and all(x.lower() in tag.lower() for x in words):
            completions_added.append(tag)

    # Add synonyms to suggestions, following same priority pattern as above.
    # First loop...
    for tag, syn_list in synonyms.items():
        for synonym in syn_list:
            for word in words:
                if tag not in completions_added and synonym.lower().startswith(word) and all(x.lower() in synonym.lower() for x in words):
                    completions_added.append(tag)
    # ...second loop.
    for tag, syn_list in synonyms.items():
        for synonym in syn_list:
            if tag not in completions_added and all(x.lower() in synonym.lower() for x in words):
                completions_added.append(tag)

    return jsonify(completions_added)


# API to retrieve descendants of a tag
@app.route('/descendants', methods=['GET'])
def get_descendants() -> Response:
    input_concept = request.args.get('q', '')
    return jsonify(descendants[input_concept])


# API to retrieve short URIs of a list of human-readable tags
@app.route('/uris', methods=['GET'])
def get_uris() -> Response:
    input_concepts = request.args.getlist('q')
    results = {concept: uris.get(concept) for concept in input_concepts}
    return jsonify(results)


# Run from terminal for testing
def run_api() -> None:
    app.run(debug=False, port=5000)


# Run in background (only used by app version)
def run_api_in_background() -> None:
    flask_thread = threading.Thread(target=run_api)
    flask_thread.daemon = True
    flask_thread.start()
    time.sleep(1)


# If running from the terminal...
if __name__ == '__main__':
    run_api()
