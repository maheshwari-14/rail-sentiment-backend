from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import xml.etree.ElementTree as ET

router = APIRouter(prefix="/ontology", tags=["ontology"])


class OWLParseRequest(BaseModel):
    owl_xml: str


def _local_name(tag: str) -> str:
    """Strip the namespace URI, return local element name."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _iri_name(iri: str) -> str:
    """Extract the readable name from an IRI like '#Cleanliness'."""
    if "#" in iri:
        return iri.split("#")[-1]
    return iri.rsplit("/", 1)[-1] if "/" in iri else iri


OWL_NS = "http://www.w3.org/2002/07/owl#"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
XSD_NS = "http://www.w3.org/2001/XMLSchema#"

NS = {
    "owl": OWL_NS,
    "rdf": RDF_NS,
    "rdfs": RDFS_NS,
    "xsd": XSD_NS,
}


def parse_owl_xml(xml_text: str) -> dict:
    """Parse OWL/XML into a structured dictionary."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML: {e}")

    classes = set()
    sub_class_of = []
    object_properties = []
    data_properties = []
    individuals = []
    data_assertions = []

    # --- Declarations ---
    for decl in root.findall("owl:Declaration", NS):
        cls = decl.find("owl:Class", NS)
        if cls is not None:
            iri = cls.get("IRI", "")
            classes.add(_iri_name(iri))

        op = decl.find("owl:ObjectProperty", NS)
        if op is not None:
            object_properties.append({"name": _iri_name(op.get("IRI", ""))})

        dp = decl.find("owl:DataProperty", NS)
        if dp is not None:
            data_properties.append({"name": _iri_name(dp.get("IRI", ""))})

        ni = decl.find("owl:NamedIndividual", NS)
        if ni is not None:
            individuals.append({
                "name": _iri_name(ni.get("IRI", "")),
                "properties": {},
            })

    # --- SubClassOf ---
    for sc in root.findall("owl:SubClassOf", NS):
        cls_elems = sc.findall("owl:Class", NS)
        if len(cls_elems) == 2:
            child = _iri_name(cls_elems[0].get("IRI", ""))
            parent = _iri_name(cls_elems[1].get("IRI", ""))
            sub_class_of.append({"child": child, "parent": parent})

    # --- DataPropertyAssertion (individual data) ---
    for dpa in root.findall("owl:DataPropertyAssertion", NS):
        dp = dpa.find("owl:DataProperty", NS)
        ni = dpa.find("owl:NamedIndividual", NS)
        lit = dpa.find("owl:Literal", NS)
        if dp is not None and ni is not None and lit is not None:
            ind_name = _iri_name(ni.get("IRI", ""))
            prop_name = _iri_name(dp.get("IRI", ""))
            value = lit.text or ""
            # Attach to existing individual
            for ind in individuals:
                if ind["name"] == ind_name:
                    ind["properties"][prop_name] = value
                    break

    # --- DataPropertyRange ---
    dp_ranges = {}
    for dpr in root.findall("owl:DataPropertyRange", NS):
        dp = dpr.find("owl:DataProperty", NS)
        dt = dpr.find("owl:Datatype", NS)
        if dp is not None and dt is not None:
            dp_ranges[_iri_name(dp.get("IRI", ""))] = _iri_name(
                dt.get("abbreviatedIRI", dt.get("IRI", ""))
            )

    # Attach ranges to data properties
    for dp in data_properties:
        dp["range"] = dp_ranges.get(dp["name"], "")

    # --- ObjectPropertyDomain / ObjectPropertyRange ---
    op_domains = {}
    op_ranges_map = {}
    for opd in root.findall("owl:ObjectPropertyDomain", NS):
        op = opd.find("owl:ObjectProperty", NS)
        if op is not None:
            op_domains[_iri_name(op.get("IRI", ""))] = True
    for opr in root.findall("owl:ObjectPropertyRange", NS):
        op = opr.find("owl:ObjectProperty", NS)
        if op is not None:
            op_ranges_map[_iri_name(op.get("IRI", ""))] = True

    for op in object_properties:
        op["hasDomain"] = op["name"] in op_domains
        op["hasRange"] = op["name"] in op_ranges_map

    return {
        "classes": sorted(classes),
        "subClassOf": sub_class_of,
        "objectProperties": object_properties,
        "dataProperties": data_properties,
        "individuals": individuals,
        "dataAssertions": data_assertions,
    }


@router.post("/parse")
async def parse_ontology(request: OWLParseRequest):
    return parse_owl_xml(request.owl_xml)
