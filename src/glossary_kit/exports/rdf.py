from __future__ import annotations

import json
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, SKOS

from glossary_kit.domain.models import Glossary

SKOS_NS = Namespace("http://www.w3.org/2004/02/skos/core#")
GLOSS_NS = Namespace("https://glossary-kit.dev/scheme/")


def _public_term_ids(glossary: Glossary) -> set[str]:
    return {t.id for t in glossary.public_terms()}


def _lang_value(text: str, language: str) -> dict[str, str]:
    return {"@value": text, "@language": language}


def export_skos_turtle(glossary: Glossary, output: Path) -> None:
    g = Graph()
    g.bind("skos", SKOS_NS)
    g.bind("dcterms", DCTERMS)
    g.bind("gloss", GLOSS_NS)

    scheme_uri = GLOSS_NS["scheme"]
    g.add((scheme_uri, RDF.type, SKOS.ConceptScheme))
    g.add((scheme_uri, DCTERMS.title, Literal(glossary.metadata.title)))
    if glossary.metadata.description:
        g.add((scheme_uri, DCTERMS.description, Literal(glossary.metadata.description)))

    public_ids = _public_term_ids(glossary)
    terms = sorted(glossary.public_terms(), key=lambda t: t.id)
    for term in terms:
        concept = GLOSS_NS[term.id]
        g.add((concept, RDF.type, SKOS.Concept))
        g.add((concept, SKOS.inScheme, scheme_uri))
        g.add((concept, SKOS.prefLabel, Literal(term.preferred_label, lang=term.language)))
        g.add((concept, SKOS.definition, Literal(term.definition, lang=term.language)))
        for syn in sorted(term.synonyms):
            g.add((concept, SKOS.altLabel, Literal(syn, lang=term.language)))
        for rel in sorted(term.related_terms):
            if rel in public_ids:
                g.add((concept, SKOS.related, GLOSS_NS[rel]))
        if term.replaces and term.replaces in public_ids:
            g.add((concept, GLOSS_NS.replaces, GLOSS_NS[term.replaces]))
        if term.replaced_by and term.replaced_by in public_ids:
            g.add((concept, GLOSS_NS.replacedBy, GLOSS_NS[term.replaced_by]))
        if term.source_url:
            g.add((concept, DCTERMS.source, URIRef(term.source_url)))

    output.parent.mkdir(parents=True, exist_ok=True)
    sorted_g = _sorted_graph(g)
    output.write_text(sorted_g.serialize(format="turtle"), encoding="utf-8")


def export_jsonld(glossary: Glossary, output: Path) -> None:
    context = {
        "@vocab": "http://www.w3.org/2004/02/skos/core#",
        "dcterms": "http://purl.org/dc/terms/",
        "gloss": "https://glossary-kit.dev/scheme/",
        "inScheme": {"@type": "@id"},
        "related": {"@type": "@id"},
        "replaces": {"@type": "@id", "@id": "gloss:replaces"},
        "replacedBy": {"@type": "@id", "@id": "gloss:replacedBy"},
        "source": {"@type": "@id", "@id": "dcterms:source"},
    }

    scheme_id = "gloss:scheme"
    graph: list[dict[str, object]] = [
        {
            "@id": scheme_id,
            "@type": "ConceptScheme",
            "dcterms:title": glossary.metadata.title,
        }
    ]

    public_ids = _public_term_ids(glossary)
    for term in sorted(glossary.public_terms(), key=lambda t: t.id):
        node: dict[str, object] = {
            "@id": f"gloss:{term.id}",
            "@type": "Concept",
            "inScheme": scheme_id,
            "prefLabel": _lang_value(term.preferred_label, term.language),
            "definition": _lang_value(term.definition, term.language),
        }
        if term.synonyms:
            node["altLabel"] = [_lang_value(syn, term.language) for syn in sorted(term.synonyms)]
        public_related = sorted(rel for rel in term.related_terms if rel in public_ids)
        if public_related:
            node["related"] = [f"gloss:{r}" for r in public_related]
        if term.replaces and term.replaces in public_ids:
            node["replaces"] = f"gloss:{term.replaces}"
        if term.replaced_by and term.replaced_by in public_ids:
            node["replacedBy"] = f"gloss:{term.replaced_by}"
        if term.source_url:
            node["source"] = term.source_url
        graph.append(node)

    doc = {"@context": context, "@graph": graph}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sorted_graph(g: Graph) -> Graph:
    sorted_g = Graph()
    for p, o, s in sorted(g, key=lambda t: (str(t[0]), str(t[1]), str(t[2]))):
        sorted_g.add((p, o, s))
    for prefix, ns in sorted(g.namespaces()):
        sorted_g.bind(prefix, ns)
    return sorted_g
