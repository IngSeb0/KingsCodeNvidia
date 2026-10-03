"""Read-only snapshot/integration verification. No rebuild, labels or GPU."""
from pathlib import Path
import copy
import json
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kingscode.common import ROOT,file_hash,read_json,read_jsonl,write_json
from kingscode.retrieval import Retriever,retrieve
from kingscode.diversify import collapse_duplicates
from kingscode.metadata import canonical_document_id
from kingscode.benchmark_v2 import check


def verify_g01_d01_reviews():
    report_root = ROOT / "reports/member_a_v02"
    g01 = read_json(report_root / "g01_relation_review_v02.json")
    if (g01.get("source_candidate_count") != 7 or
        g01.get("rejected_wrong_container_target") != 7 or
        g01.get("replacement_relations_unresolved") != 7 or
        g01.get("accepted_semantic_relations") != 0 or
        g01.get("active_semantic_edges") != 0):
        raise ValueError("G01 review status/edge activation changed unexpectedly")
    if any(row.get("replacement_relation_active") for row in g01["relations"]):
        raise ValueError("G01 contains an unverified active replacement relation")

    findings = read_jsonl(report_root / "corpus_audit_findings_v07.jsonl")
    d01 = next((row for row in findings if row.get("finding_id") == "D01"), None)
    if d01 is None or len(d01.get("evidence", [])) != 7:
        raise ValueError("D01 source-backed collision groups changed")
    document_count = 0
    for group in d01["evidence"]:
        rows = []
        for index, document_id in enumerate(group["canonical_documents"]):
            court, compact_docket, year = document_id.split(":")
            match = re.fullmatch(r"([a-z]+)(\d+)", compact_docket)
            if court != "corte_constitucional" or match is None:
                raise ValueError("Unrecognized D01 canonical decision identity")
            docket = f"{match.group(1).upper()}-{match.group(2)}"
            rows.append({"passage_id": f"{document_id}:verify:{index}",
                         "doc_id": f"sentencia_{match.group(1)}_{match.group(2)}_de_{year}",
                         "source_type": "decision",
                         "canonical_body": ["jurisprudencia", docket, year],
                         "text": group["body"],
                         "source_url": f"https://official.example/{document_id}"})
        expected = set(group["canonical_documents"])
        if {canonical_document_id(row) for row in rows} != expected:
            raise ValueError("D01 canonical document identity did not round-trip")
        collapsed = collapse_duplicates(rows, level="content")
        actual = {canonical_document_id(row) for row in collapsed}
        if actual != expected or any(len(row["duplicate_group"]["members"]) != 1 for row in collapsed):
            raise ValueError("D01 content dedup merged distinct canonical legal works")
        document_count += len(rows)
    if document_count != 22:
        raise ValueError("D01 reviewed document count changed")
    return {"g01_wrong_container_targets_rejected": 7,
            "g01_replacement_relations_unresolved_inactive": 7,
            "g01_active_semantic_edges": 0,
            "d01_content_hash_groups": 7,
            "d01_group_document_occurrences": document_count,
            "d01_cross_document_content_collapses": 0}


def _timing_free(rows):
    """Copy of retrieve() rows without wall-clock *_ms profile telemetry."""
    out=[]
    for row in rows:
        row=copy.deepcopy(row)
        profile=(row.get('retrieval') or {}).get('profile')
        if isinstance(profile,dict):
            for key in [k for k in profile if k.endswith('_ms')]:profile.pop(key)
        out.append(row)
    return out


def verify():
    review_checks = verify_g01_d01_reviews()
    official={}
    for line in (ROOT/'docs/OFFICIAL_SHA256.txt').read_text(encoding='utf-8-sig').splitlines():
        if line.strip():
            expected,name=line.split('  ',1)
            if file_hash(ROOT/name)!=expected:raise ValueError('Official changed: '+name)
            official[name]=expected
    # B-owned paths (kingscode/reasoning, config/reasoning.json) are excluded: B's
    # own merged work legitimately changes them and B verifies them with its tests.
    # Compare protected files to the branch point with current origin/main. This
    # preserves the guard for task-branch commits and worktree edits while not
    # treating legitimate protected-path changes already shipped on main as local drift.
    protected=['config/models.lock.json','config/neural.json','data','schema','scripts','benchmarks/kingscode_ir',
               'tools/gpu_search_v2_dev.py','tools/gpu_search_v2_validation.py','reports/gpu_freeze_4090',
               'reports/benchmark/search_v2','reports/benchmark/search_v2_validation']
    upstream=subprocess.check_output(['git','rev-parse','--verify','origin/main'],cwd=ROOT,text=True).strip()
    branch_point=subprocess.check_output(['git','merge-base','HEAD',upstream],cwd=ROOT,text=True).strip()
    branch_diff=subprocess.check_output(['git','diff',branch_point,'HEAD','--',*protected],cwd=ROOT)
    worktree_diff=subprocess.check_output(['git','diff','HEAD','--',*protected],cwd=ROOT)
    if branch_diff or worktree_diff:raise ValueError('Protected B/official/historical GPU/benchmark/model files changed on this branch or worktree')
    snapshot=read_json(ROOT/'corpus/manifest.json')
    actual={}
    for name,expected in {**snapshot['hashes'],'index/bm25.json':snapshot['bm25_sha256']}.items():
        actual[name]=file_hash(ROOT/'corpus'/name)
        if actual[name]!=expected:raise ValueError('Historical corpus changed: '+name)
    # Recheck every acquired raw/clean body, not only the passage manifest.
    for d in snapshot['documentos']:
        for key,hash_key in (('raw_path','source_sha256'),('clean_path','sha256')):
            if file_hash(ROOT/d[key])!=d[hash_key]:raise ValueError('Trace changed: '+d['doc_id'])
    query='Ley 1564 de 2012 artículo 90'
    legacy=Retriever()
    explicit_legacy=Retriever(exact_locator=False)
    legacy_rows=legacy.retrieve(query,8,'off')
    # retrieval.profile carries wall-clock *_ms telemetry (2026-10-01); timings differ between
    # identical calls, so determinism is checked on everything except those fields.
    if _timing_free(legacy_rows)!=_timing_free(explicit_legacy.retrieve(query,8,'off')):raise ValueError('Legacy mismatch')
    public=retrieve(query,8,'off')
    replay=retrieve(query,8,'off')
    if _timing_free(public)!=_timing_free(replay):raise ValueError('Public locator replay differs')
    if not public or not all('locator' in p for p in public):raise ValueError('Public locator profile missing')
    required={'passage_id','doc_id','text','norm_name','source_url','hierarchy_path','graph_node_ids','scores'}
    if any(not required<=p.keys() for p in public):raise ValueError('A/B passage contract incomplete')
    v02=read_json(ROOT/'corpora/corpus-v0.2/manifest.json')
    for name,expected in v02['hashes'].items():
        if file_hash(ROOT/'corpora/corpus-v0.2'/name)!=expected:raise ValueError('v0.2 artifact mismatch: '+name)
    result={'status':'PASS','scope':'CPU read-only snapshot/API verification; not GPU metric replay',
            'official_files_unchanged':len(official),'v01_raw_clean_files_unchanged':2*len(snapshot['documentos']),
            'v01_core_hashes':actual,'protected_git_diff_empty':True,'legacy_compatible':True,
            'public_retrieve_deterministic':True,'public_passage_contract':sorted(required),
            'v02_hashes_verified':len(v02['hashes']),'benchmark_v2':check(),
            'source_relation_and_identity_review':review_checks,
            'gpu_executed':False,'holdout_executed':False,'old_rebuild_verifier':'Not run: rebuild/official-50 replay are outside this phase.'}
    write_json(ROOT/'reports/member_a_v02/verification.json',result)
    return result


if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False,indent=2))
