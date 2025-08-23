import re, sys, os, datetime
from datetime import timezone
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import OWL, DCTERMS, XSD
from rdflib.namespace import RDF

import dotenv
# read from a local .env file
dotenv.load_dotenv()

if "ONTO_ABBREV" in os.environ:
    onto_abbrev = os.environ["ONTO_ABBREV"]
else:
    # write error
    print("Error: ONTO_ABBREV not found in environment variables.")
    sys.exit(1)

if "ONTO_FILE" in os.environ:
    onto_file = os.environ["ONTO_FILE"]
else:
    # write error
    print("Warning: ONTO_FILE not found in environment variables.")
    # create the file
    onto_file = f"{onto_abbrev}.ttl"
    print(f"Info: Using default filename: {onto_file}")

if "BASE_IRI" in os.environ:
    base_iri = os.environ["BASE_IRI"]
    # add a trailing slash if not present
    if not base_iri.endswith("/"):
        base_iri += "/"
else:
    # write error
    print("Warning: BASE_IRI not found in environment variables.")
    base_iri = f"https://w3id.org/{onto_abbrev}/"
    print(f"Info: Using default base IRI: {base_iri}")

if "VERSION_DIR" in os.environ:
    version_dir = os.environ["VERSION_DIR"]
else:
    # write error
    print("Warning: VERSION_DIR not found in environment variables.")
    version_dir = "versions"
    print(f"Info: Using default version directory: {version_dir}")


#### automatic after this
onto_iri = URIRef(base_iri) 
today = datetime.date.today().isoformat()
today_datetime = datetime.datetime.now(timezone.utc).astimezone().isoformat()

g = Graph()
g.parse(onto_file)
ONTO = Namespace(base_iri)
g.bind(onto_abbrev, ONTO)
MOD = Namespace("https://w3id.org/mod#")
g.bind("mod", MOD)

# check if the graph has any triples
if len(g) == 0:
    print(f"ERROR: {onto_file} is empty or not valid.")
    sys.exit(1)

# check that there is a triple with base_iri rdf:type owl:Ontology
ontos = list(g.subjects(RDF.type, OWL.Ontology))
if onto_iri not in ontos:
    print(f"ERROR: {base_iri} is not typed an owl:Ontology.")
    sys.exit(1)

# Get current versionInfo (semver expected; default to 0.0.0)
current_vi = None
for _, _, o in g.triples((onto_iri, OWL.versionInfo, None)):
    current_vi = str(o)
    break
if current_vi is None:
    current_vi = "0.0.0"

m = re.match(r'^(\d+)\.(\d+)\.(\d+)$', current_vi.strip())
if not m:
# If not semver, start at 0.0.0
    m = (0,0,0)
    major, minor, patch = 0,0,0
else:
    major, minor, patch = map(int, m.groups())

current_version_dir = f"{version_dir}/{current_vi}"
current_version_iri = URIRef(f"{base_iri}{current_vi}")
current_version_file = f"{current_version_dir}/{onto_abbrev}.ttl"

### add any missing metadata to the current version
# if not any(g.triples((onto_iri, MOD.URI, None))):
#     g.add((onto_iri, MOD.URI, Literal(current_version_iri, datatype=XSD.anyURI)))

# if not any(g.triples((onto_iri, OWL.versionInfo, None))):
#     g.add((onto_iri, OWL.versionInfo, Literal(current_vi, datatype=XSD.string)))
    
# if not any(g.triples((onto_iri, OWL.versionIRI, None))):
#     g.add((onto_iri, OWL.versionIRI, current_version_iri))

# if not any(g.triples((onto_iri, DCTERMS.created, None))):
#     g.add((onto_iri, DCTERMS.created, Literal(today, datatype=XSD.date)))
    
# if not any(g.triples((onto_iri, DCTERMS.modified, None))):
#     g.add((onto_iri, DCTERMS.modified, Literal(today, datatype=XSD.date)))
           
# if not any(g.triples((onto_iri, DCTERMS.issued, None))):
#     g.add((onto_iri, DCTERMS.issued, Literal(today, datatype=XSD.date)))

# # write the current IRI file to the version directory.
# if not os.path.exists(current_version_file):
#     # create the directory
#     os.makedirs(current_version_dir, exist_ok=True)
#     g.serialize(destination=current_version_file, format="turtle")

# now update the ontology with the new versioning info
# Bump patch
patch += 1
new_vi = f"{major}.{minor}.{patch}"
new_version_dir = f"{version_dir}/{new_vi}"
new_version_iri = URIRef(f"{base_iri}{new_vi}")
new_version_file = f"{new_version_dir}/{onto_abbrev}.ttl"

g.remove((onto_iri, OWL.versionIRI, None))
g.remove((onto_iri, OWL.versionInfo, None))
g.remove((onto_iri, DCTERMS.created, None))
g.remove((onto_iri, DCTERMS.modified, None))
g.remove((onto_iri, DCTERMS.issued, None))
g.remove((onto_iri, OWL.priorVersion, None))
g.remove((onto_iri, OWL.backwardCompatibleWith, None))

g.add((onto_iri, OWL.versionIRI, new_version_iri))
g.add((onto_iri, OWL.versionInfo, Literal(new_vi, datatype=XSD.string)))
g.add((onto_iri, DCTERMS.created, Literal(today_datetime, datatype=XSD.dateTime)))
g.add((onto_iri, DCTERMS.modified, Literal(today_datetime, datatype=XSD.dateTime)))
g.add((onto_iri, DCTERMS.issued, Literal(today, datatype=XSD.date)))
if os.path.exists(current_version_file):
    g.add((onto_iri, OWL.priorVersion, current_version_iri))
    g.add((onto_iri, OWL.backwardCompatibleWith, current_version_iri))

# write new versioned files
os.makedirs(new_version_dir, exist_ok=True)
g.serialize(destination=new_version_file, format="turtle")
g.serialize(destination=onto_file, format="turtle")

print(f"NEW_FILE={new_version_file}")
print(f"NEW_VERSION={new_vi}")

if "GITHUB_OUTPUT" in os.environ:
    with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
        fh.write(f"NEW_FILE={new_version_file}\n")
        fh.write(f"NEW_VERSION={new_vi}\n")