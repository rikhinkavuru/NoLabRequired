#!/usr/bin/env python
"""Pull every externally-sourced fact the book states, and record its provenance.

Run this before drafting, and again before each release. Anything the book
asserts about a database record must appear in research/facts.jsonl with a URL
and a retrieval date; the dataset index at the back of the book is generated
from the same file.

    .venv/bin/python tools/fetch_facts.py [group ...]

Groups: gene, protein, structure, expression, all
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import facts  # noqa: E402


def _gb_field(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text, re.M)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------------------
# Genes: the Chapter 5 walkthrough and its mouse comparison
# ---------------------------------------------------------------------------
def group_gene() -> None:
    for tag, uid in (("human", "672"), ("mouse", "12189")):
        payload, url = facts.esummary_json("gene", uid)
        rec = payload["result"][uid]
        raw = f"ncbi_gene_{uid}.json"
        facts.save_raw(raw, json.dumps(payload, indent=2))
        gi = rec["genomicinfo"][0]
        start, stop = gi["chrstart"], gi["chrstop"]
        page = f"https://www.ncbi.nlm.nih.gov/gene/{uid}"
        common = dict(source_url=page, method="NCBI E-utilities esummary db=gene", raw_file=raw)

        facts.record(f"brca1.{tag}.gene_id", uid, **common)
        facts.record(f"brca1.{tag}.symbol", rec["name"], **common)
        facts.record(f"brca1.{tag}.description", rec["description"], **common)
        facts.record(f"brca1.{tag}.organism", rec["organism"]["scientificname"], **common)
        facts.record(f"brca1.{tag}.taxid", rec["organism"]["taxid"], **common)
        facts.record(f"brca1.{tag}.chromosome", rec["chromosome"], **common)
        facts.record(f"brca1.{tag}.maplocation", rec["maplocation"], **common)
        facts.record(f"brca1.{tag}.genomic_accession", gi["chraccver"], **common)
        facts.record(f"brca1.{tag}.genomic_start", start, **common)
        facts.record(f"brca1.{tag}.genomic_stop", stop, **common)
        facts.record(
            f"brca1.{tag}.genomic_span_bp", abs(start - stop) + 1, unit="bp",
            note="chrstart to chrstop inclusive, from esummary genomicinfo", **common,
        )
        facts.record(
            f"brca1.{tag}.strand", "minus" if start > stop else "plus",
            note="inferred: esummary reports chrstart > chrstop for minus-strand genes", **common,
        )
        facts.record(
            f"brca1.{tag}.exoncount_genomicinfo", gi["exoncount"],
            note="esummary genomicinfo exoncount; counts exons across all annotated transcripts",
            **common,
        )
        facts.record(f"brca1.{tag}.aliases", rec.get("otheraliases", ""), **common)

        summary = rec.get("summary", "")
        facts.record(f"brca1.{tag}.ncbi_summary", summary, **common)
        m = re.search(r"contains (\d+) exons", summary)
        if m:
            facts.record(
                f"brca1.{tag}.exoncount_summary_text", int(m.group(1)),
                note="number stated in the prose summary on the Gene record; "
                     "deliberately differs from exoncount_genomicinfo and from the "
                     "exon feature count on the MANE transcript",
                **common,
            )

    # RefSeq transcripts and proteins
    for tag, acc in (("human", "NM_007294"), ("mouse", "NM_009764")):
        text, url = facts.efetch("nuccore", acc, rettype="gb", retmode="text")
        raw = f"{acc}_gb.txt"
        facts.save_raw(raw, text)
        page = f"https://www.ncbi.nlm.nih.gov/nuccore/{acc}"
        common = dict(source_url=page, method="NCBI E-utilities efetch rettype=gb", raw_file=raw)

        version = _gb_field(text, r"^VERSION\s+(\S+)")
        length = _gb_field(text, r"^LOCUS\s+\S+\s+(\d+) bp")
        definition = " ".join(
            line.strip()
            for line in re.search(r"^DEFINITION\s+(.*?)^ACCESSION", text, re.S | re.M).group(1).splitlines()
        )
        exon_features = len(re.findall(r"^     exon\s+", text, re.M))
        protein_id = _gb_field(text, r'/protein_id="([^"]+)"')
        translation = re.search(r'/translation="([^"]+)"', text, re.S)
        aa = len(re.sub(r"\s+", "", translation.group(1))) if translation else None
        cds = _gb_field(text, r"^     CDS\s+(\S+)")
        mane = "MANE Select" in text

        facts.record(f"brca1.{tag}.mrna_accession", version, **common)
        facts.record(f"brca1.{tag}.mrna_length_nt", int(length), unit="bp", **common)
        facts.record(f"brca1.{tag}.mrna_definition", definition, **common)
        facts.record(
            f"brca1.{tag}.exoncount_mane_transcript", exon_features,
            note="count of `exon` features in the GenBank flatfile for this transcript",
            **common,
        )
        facts.record(f"brca1.{tag}.cds_range", cds, **common)
        facts.record(f"brca1.{tag}.is_mane_select", mane, **common)
        facts.record(f"brca1.{tag}.protein_accession", protein_id, **common)
        if aa:
            facts.record(f"brca1.{tag}.protein_length_aa", aa, unit="aa", **common)


# ---------------------------------------------------------------------------
# Proteins: Chapter 8, UniProt
# ---------------------------------------------------------------------------
UNIPROT_ACCS = {
    "brca1_human": "P38398",
    "lysozyme_human": "P61626",
    "hbb_human": "P68871",
}


def group_protein() -> None:
    for tag, acc in UNIPROT_ACCS.items():
        text, url = facts.fetch(f"https://rest.uniprot.org/uniprotkb/{acc}.json")
        payload = json.loads(text)
        raw = f"uniprot_{acc}.json"
        facts.save_raw(raw, json.dumps(payload, indent=2))
        page = f"https://www.uniprot.org/uniprotkb/{acc}"
        common = dict(source_url=page, method="UniProt REST /uniprotkb/{acc}.json", raw_file=raw)

        facts.record(f"uniprot.{tag}.accession", payload["primaryAccession"], **common)
        facts.record(f"uniprot.{tag}.entry_name", payload["uniProtkbId"], **common)
        facts.record(f"uniprot.{tag}.length_aa", payload["sequence"]["length"], unit="aa", **common)
        facts.record(f"uniprot.{tag}.mass_da", payload["sequence"]["molWeight"], unit="Da", **common)
        facts.record(f"uniprot.{tag}.reviewed", payload["entryType"], **common)
        names = payload.get("proteinDescription", {}).get("recommendedName", {})
        if names:
            facts.record(f"uniprot.{tag}.recommended_name", names["fullName"]["value"], **common)
        domains = [
            f"{f['type']} {f['location']['start']['value']}-{f['location']['end']['value']}"
            f"{(': ' + f['description']) if f.get('description') else ''}"
            for f in payload.get("features", [])
            if f["type"] in ("Domain", "Zinc finger", "Region")
        ]
        facts.record(f"uniprot.{tag}.domain_features", domains[:40], **common)
        pdb_xrefs = [x["id"] for x in payload.get("uniProtKBCrossReferences", []) if x["database"] == "PDB"]
        facts.record(f"uniprot.{tag}.pdb_count", len(pdb_xrefs), **common)
        facts.record(f"uniprot.{tag}.pdb_ids", pdb_xrefs[:30], **common)


# ---------------------------------------------------------------------------
# Structures: Chapter 8, PDB and AlphaFold DB
# ---------------------------------------------------------------------------
def group_structure() -> None:
    for pdb_id in ("1JNX", "1T15"):
        text, url = facts.fetch(f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}")
        payload = json.loads(text)
        raw = f"pdb_{pdb_id}.json"
        facts.save_raw(raw, json.dumps(payload, indent=2))
        page = f"https://www.rcsb.org/structure/{pdb_id}"
        common = dict(source_url=page, method="RCSB PDB Data API /core/entry", raw_file=raw)
        facts.record(f"pdb.{pdb_id}.title", payload["struct"]["title"], **common)
        facts.record(
            f"pdb.{pdb_id}.method",
            [e["method"] for e in payload.get("exptl", [])],
            **common,
        )
        res = payload.get("rcsb_entry_info", {}).get("resolution_combined")
        if res:
            facts.record(f"pdb.{pdb_id}.resolution_angstrom", res[0], unit="A", **common)
        facts.record(
            f"pdb.{pdb_id}.deposited",
            payload.get("rcsb_accession_info", {}).get("deposit_date", "")[:10],
            **common,
        )

    for tag, acc in (("brca1_human", "P38398"),):
        text, url = facts.fetch(f"https://alphafold.ebi.ac.uk/api/prediction/{acc}")
        payload = json.loads(text)
        raw = f"alphafold_{acc}.json"
        facts.save_raw(raw, json.dumps(payload, indent=2))
        entry = payload[0]
        page = f"https://alphafold.ebi.ac.uk/entry/{acc}"
        common = dict(source_url=page, method="AlphaFold DB API /api/prediction", raw_file=raw)
        facts.record(f"alphafold.{tag}.entry_id", entry["entryId"], **common)
        facts.record(f"alphafold.{tag}.model_version", entry.get("latestVersion"), **common)
        facts.record(f"alphafold.{tag}.model_created", entry.get("modelCreatedDate"), **common)
        facts.record(f"alphafold.{tag}.sequence_length", len(entry["uniprotSequence"]), unit="aa", **common)
        facts.record(f"alphafold.{tag}.cif_url", entry.get("cifUrl", ""), **common)


GROUPS = {
    "gene": group_gene,
    "protein": group_protein,
    "structure": group_structure,
}


def main(argv: list[str]) -> int:
    wanted = argv[1:] or ["all"]
    names = list(GROUPS) if "all" in wanted else wanted
    for name in names:
        fn = GROUPS.get(name)
        if fn is None:
            print(f"unknown group: {name}", file=sys.stderr)
            return 2
        print(f"--- {name} ---")
        fn()
    total = len(facts.all_facts())
    print(f"\nfacts.jsonl now holds {total} verified records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
