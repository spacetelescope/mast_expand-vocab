An attempt to match every SIMBAD object type to at least one UAT concept. Note that much of this has already been done by the IVOA in the object type vocabulary RDF file (search for skos:exactMatch in their file). I mostly redid it to get a feel for how the two vocabularies are structured and how they differ. However, there are some differences here from the IVOA matching:

-more match types than just exactMatch (broadMatch, closeMatch, and in my comments sometimes narrowMatch)

-human-readable, based on UAT v5.0 and the new (2022) SIMBAD vocab, for temporary convenience

-incorporates new terms from the 2022 revision to the SIMBAD vocab (of which there are only a few)

-incorporates older/deprecated SIMBAD terms that aren't in the IVOA vocab

-differences of opinion (probably extremely rare, although this has not yet been checked carefully) on what the best match is / whether there is a match

*********

In SKOS, broadMatch means "(object) is broader than (subject)". For example, Yellow supergiant SKOS:broadMatch Supergiants means that Supergiants is broader than Yellow supergiant. Likewise for narrowMatch.

exactMatch means there is an exact match.

closeMatch is being used here to denote that there is an almost exact match, but that there are differences that concern me or that the two concepts could drift away from each other as their respective vocabularies evolve.

relatedMatch is being used here to denote similar concepts when a good match does not exist. This does not necessarily imply that the two concepts should connect to each other in a hierarchy.

**********

My columns are "SKOS relationship", "UAT match", and "ABL comments". The rest of the columns are from a direct download of the new 2022 version of the SIMBAD o-type vocabulary.
