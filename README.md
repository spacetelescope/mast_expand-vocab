# mast_expand-vocab
This repo contains some of the draft vocabularies being worked on by MAST staff, currently focused on vocabularies for High Level Science Products (with potential long-term interest in MCCMs, other data collections that aren't consistently available in CAOM, and query expansion/travel between different collections/unified search). 

Currently an extremely preliminary rough draft---intended as a starting place for conversations, and as something for developers to use while working on prototypes.

Contents include the following folders:

## demo_code

``get_vocab_demo.ipynb`` : demo code for dumping a SKOS vocabulary into a database using rdflib

``typeahead_terminal_demo.py`` : command-line program wired to the draft data product type vocabulary, used to demonstrate typeahead with sophisticated synonym and hierarchy support

``rdflib-sparql_transitive_demo.ipynb`` : demo code for traveling up/down a vocabulary hierarchy with transitive inference using rdflib

## vocabs

This folder contains draft vocabularies in SKOS RDF files, and visualizations of those vocabularies in the viz subfolder.

## misc

This folder contains miscellaneous content, such as exploratory attempts to map the SIMBAD/IVOA object type vocabulary to the UAT, etc.
