#!/usr/bin/env python
"""Run the book's BLAST searches for real and keep the results.

Every hit table printed in Chapters 6 and 7 comes from here. No invented
E-values, no plausible-looking bit scores, no hit tables assembled from memory.
The searches are slow because NCBI queues them, so this writes everything to
data/blast/ and is safe to re-run: a query whose result is already on disk is
skipped.

NCBI's usage policy for the URL API asks for no more than one submission every
10 seconds and polling no more often than once a minute. Both are honoured.

    .venv/bin/python tools/fetch_blast.py
"""
from __future__ import annotations

import json
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import facts  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "blast"
SEQ = ROOT / "data" / "sequences"
BLAST_URL = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
UA = {"User-Agent": facts.UA}


def read_fasta_seq(text: str) -> str:
    return "".join(l.strip() for l in text.splitlines() if not l.startswith(">"))


def fetch_fasta(accession: str) -> str:
    text, _ = facts.efetch("nuccore", accession, rettype="fasta", retmode="text")
    return text.strip() + "\n"


def submit(query: str, program: str, database: str, **extra) -> str:
    params = {
        "CMD": "Put",
        "PROGRAM": program,
        "DATABASE": database,
        "QUERY": query,
        "HITLIST_SIZE": "50",
        "EMAIL": "rikhin@virahacks.com",
        "TOOL": "no-lab-required-workbook",
        **extra,
    }
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(BLAST_URL, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode()
    rid = re.search(r"^    RID = (\S+)", body, re.M)
    if not rid:
        raise RuntimeError("no RID returned; NCBI said:\n" + body[:800])
    return rid.group(1)


def wait(rid: str, timeout_s: int = 2400) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        time.sleep(60)
        url = f"{BLAST_URL}?CMD=Get&FORMAT_OBJECT=SearchInfo&RID={rid}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as resp:
            body = resp.read().decode()
        if "Status=WAITING" in body:
            print(f"    {rid} waiting")
            continue
        if "Status=FAILED" in body or "Status=UNKNOWN" in body:
            raise RuntimeError(f"{rid} failed: {body[:400]}")
        if "Status=READY" in body:
            if "ThereAreHits=yes" in body:
                print(f"    {rid} ready, hits found")
            else:
                print(f"    {rid} ready, NO hits")
            return
    raise TimeoutError(f"{rid} still running after {timeout_s}s")


def validate(report_json: str, name: str) -> None:
    """Refuse to keep a search that failed but reported itself as empty.

    NCBI returns HTTP 200 and Status=READY for a search that died server-side,
    and the JSON then says "No hits found" with an error tucked into a message
    field. A protein query that really has thousands of homologs comes back
    looking like a clean negative result.

    The tell is the database statistics. A search that ran reports how many
    sequences and letters it looked at. A search that failed reports zero, and
    zero sequences searched is not evidence of anything.
    """
    payload = json.loads(report_json)
    search = payload["BlastOutput2"][0]["report"]["results"]["search"]
    stat = search.get("stat", {})
    message = search.get("message", "")

    if stat.get("db_num", 0) <= 0 or stat.get("db_len", 0) <= 0:
        raise RuntimeError(
            f"{name}: the search did not run. NCBI reported "
            f"db_num={stat.get('db_num')} db_len={stat.get('db_len')}.\n"
            f"message: {message[:300]}"
        )
    if "Error:" in message:
        raise RuntimeError(f"{name}: NCBI reported an error: {message[:300]}")


def retrieve(rid: str, fmt: str, **extra) -> str:
    params = {"CMD": "Get", "RID": rid, "FORMAT_TYPE": fmt, **extra}
    url = f"{BLAST_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as resp:
        return resp.read().decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# The queries
# ---------------------------------------------------------------------------
# A real, documented consumer story: fish sold under one name and sequenced as
# another. Both records are real GenBank COI barcodes.
POLLOCK = "MN850428.1"   # Gadus chalcogrammus, Alaska pollock, 649 bp
COD = "MT456169.1"       # Gadus morhua, Atlantic cod, 655 bp


def build_queries() -> list[dict]:
    SEQ.mkdir(parents=True, exist_ok=True)

    pollock_fa = fetch_fasta(POLLOCK)
    cod_fa = fetch_fasta(COD)
    (SEQ / "cod_reference_MT456169.fasta").write_text(cod_fa)

    # The unknown the reader identifies. The header is stripped to a neutral
    # label so the answer is not printed on the question.
    pollock_seq = read_fasta_seq(pollock_fa)
    mystery = ">mystery_fillet_1\n" + "\n".join(
        pollock_seq[i : i + 60] for i in range(0, len(pollock_seq), 60)
    ) + "\n"
    (SEQ / "mystery_fillet_1.fasta").write_text(mystery)

    # The honest negative control: the same letters in a different order. Same
    # length, same base composition, no biological history. Seeded so it is
    # reproducible from the repository.
    rng = random.Random(20260802)
    shuffled = list(pollock_seq)
    rng.shuffle(shuffled)
    shuffled_seq = "".join(shuffled)
    shuffled_fa = ">shuffled_control\n" + "\n".join(
        shuffled_seq[i : i + 60] for i in range(0, len(shuffled_seq), 60)
    ) + "\n"
    (SEQ / "shuffled_control.fasta").write_text(shuffled_fa)

    facts.record(
        "blast.mystery1.true_identity", POLLOCK,
        source_url=f"https://www.ncbi.nlm.nih.gov/nuccore/{POLLOCK}",
        method="NCBI efetch rettype=fasta",
        note="Gadus chalcogrammus (Alaska pollock) COI barcode, used as the unknown in Exercise 6.1",
    )
    facts.record(
        "blast.mystery1.length_bp", len(pollock_seq), unit="bp",
        source_url=f"https://www.ncbi.nlm.nih.gov/nuccore/{POLLOCK}",
        method="len() of the fetched sequence",
    )
    facts.record(
        "blast.shuffled_control.seed", 20260802,
        source_url="tools/fetch_blast.py",
        method="random.Random(seed).shuffle over the mystery_fillet_1 sequence",
        note="same length and base composition as the real barcode, no shared history",
    )

    # Chapter 7 needs hit tables that are not all perfect. These four are
    # chosen so that ranking them by "how much do I believe this" requires
    # reading four different columns, and so that the obvious ranking by
    # percent identity is the wrong one.
    brca1_fa = fetch_fasta("NM_007294.4")
    brca1_seq = read_fasta_seq(brca1_fa)
    # A 28-base fragment, long enough to hit hundreds of things by chance and
    # short enough that every hit is meaningless. This is the counterexample to
    # "100 percent identity means it is the same gene".
    fragment = brca1_seq[600:628]
    frag_fa = f">brca1_fragment_28bp\n{fragment}\n"
    (SEQ / "brca1_fragment_28bp.fasta").write_text(frag_fa)
    facts.record(
        "blast.fragment28.sequence", fragment,
        source_url="https://www.ncbi.nlm.nih.gov/nuccore/NM_007294.4",
        method="bases 601 to 628 of NM_007294.4, 1-based inclusive",
        note="28 bases, taken from the middle of the human BRCA1 transcript",
    )

    protein_fa, _ = facts.efetch("protein", "NP_009225.1", rettype="fasta", retmode="text")

    return [
        dict(name="mystery_fillet_1_nt", query=mystery, program="blastn",
             database="nt", MEGABLAST="on"),
        dict(name="shuffled_control_nt", query=shuffled_fa, program="blastn",
             database="nt", MEGABLAST="on"),
        dict(name="cod_reference_nt", query=cod_fa, program="blastn",
             database="nt", MEGABLAST="on"),
        # A real cross-species search: the human transcript, with human itself
        # excluded, so the best available answer is a genuine ortholog rather
        # than the query looking at its own reflection.
        dict(name="brca1_human_vs_nonhuman", query=brca1_fa, program="blastn",
             database="nt", MEGABLAST="on",
             ENTREZ_QUERY="all[filter] NOT Homo sapiens[orgn]"),
        # Short query, high identity, no meaning.
        dict(name="brca1_fragment_28bp", query=frag_fa, program="blastn",
             database="nt", MEGABLAST="off", WORD_SIZE="7", EXPECT="1000"),
        # Protein against protein, where homology survives across much greater
        # distance than nucleotide identity does.
        dict(name="brca1_protein_vs_nr", query=protein_fa, program="blastp",
             database="nr",
             ENTREZ_QUERY="all[filter] NOT Homo sapiens[orgn] NOT Pan troglodytes[orgn]"),
    ]


# Tabular is not requested. Through the URL API it returns only a status stub,
# which looks like a result file and contains nothing.
FORMATS = {
    "txt": dict(fmt="Text"),
    "json": dict(fmt="JSON2_S"),
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    queries = build_queries()
    for q in queries:
        marker = OUT / f"{q['name']}.txt"
        if marker.exists() and marker.stat().st_size > 0:
            print(f"{q['name']}: already on disk, skipping")
            continue
        print(f"{q['name']}: submitting {q['program']} against {q['database']}")
        extra = {k: v for k, v in q.items() if k not in ("name", "query", "program", "database")}
        rid = submit(q["query"], q["program"], q["database"], **extra)
        print(f"    RID {rid}")
        wait(rid)
        # Fetch and validate the structured report before writing anything, so
        # a failed search never lands on disk looking like a result.
        report = retrieve(rid, FORMATS["json"]["fmt"])
        validate(report, q["name"])
        for suffix, spec in FORMATS.items():
            body = report if suffix == "json" else retrieve(rid, spec["fmt"])
            (OUT / f"{q['name']}.{suffix}").write_text(body)
            print(f"    wrote {q['name']}.{suffix} ({len(body):,} bytes)")
        (OUT / f"{q['name']}.rid").write_text(rid)
        time.sleep(12)  # NCBI: no more than one submission per 10 seconds
    print("\nall BLAST searches done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
