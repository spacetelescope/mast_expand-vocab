from rdflib import Graph, Namespace
from flask import Flask, request, jsonify
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


@app.route('/autocomplete', methods=['GET'])
def get_completions():
    input_text = request.args.get('q', '')
    words = input_text.split()

    completions_added = []

    # Check if the current word is already a complete tag
    for tag in tags:
        if (input_text.lower() == tag.lower()) and input_text not in completions_added:
            completions_added.append(tag)

    # Suggest tags that contain all the input space-separated strings.
    # First loop is to prioritize tags that start one of the space-separated strings.
    for tag in tags:
        for word in words:
            if tag.lower().startswith(word) and all(x.lower() in tag.lower() for x in words) and tag not in completions_added:
                completions_added.append(tag)
    for tag in tags:
        if tag not in completions_added and all(x.lower() in tag.lower() for x in words):
            completions_added.append(tag)

    # Add synonyms to suggestions
    for tag, syn_list in synonyms.items():
        for synonym in syn_list:
            for word in words:
                if tag not in completions_added and synonym.lower().startswith(word) and all(x.lower() in synonym.lower() for x in words):
                    completions_added.append(tag)
    for tag, syn_list in synonyms.items():
        for synonym in syn_list:
            if tag not in completions_added and all(x.lower() in synonym.lower() for x in words):
                completions_added.append(tag)

    return jsonify(completions_added)


@app.route('/descendants', methods=['GET'])
def get_descendants():
    input_concept = request.args.get('q', '')
    if input_concept in tags:
        return jsonify(descendants[input_concept])


def run_api():
    app.run(debug=False, port=5000)


# Only used by app version
def run_api_in_background():
    flask_thread = threading.Thread(target=run_api)
    flask_thread.daemon = True
    flask_thread.start()
    time.sleep(1)


if __name__ == '__main__':
    run_api()
