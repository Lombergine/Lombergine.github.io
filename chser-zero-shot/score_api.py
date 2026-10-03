"""Score a run_claude.py output file under both normalizations.

  python score_api.py outputs/api_nbest.jsonl

Reports raw pooled WER for the utterances in the file. For the 600-utterance sample,
evaluate.py gives the source-weighted estimate; for the full test split, pooled WER
is directly comparable to CHSER Table 3 and Table 4.
"""
import json, sys
import jiwer
from evaluate import paper_norm_pred, paper_norm_ref, fair_norm

recs = [json.loads(l) for l in open(sys.argv[1])]
refs_p = [paper_norm_ref(r["reference"]) for r in recs]
base_p = [paper_norm_ref(r["best"]) for r in recs]
corr_p = [paper_norm_pred(r["response"]) for r in recs]
refs_f = [fair_norm(r["reference"]) for r in recs]
base_f = [fair_norm(r["best"]) for r in recs]
corr_f = [fair_norm(r["response"]) for r in recs]

print(f"n = {len(recs)}  model = {recs[0]['model']}  prompt = {recs[0]['prompt']}")
print(f"paper normalization: baseline {100*jiwer.wer(refs_p, base_p):.2f}  corrected {100*jiwer.wer(refs_p, corr_p):.2f}")
print(f"fair normalization:  baseline {100*jiwer.wer(refs_f, base_f):.2f}  corrected {100*jiwer.wer(refs_f, corr_f):.2f}")
multi = sum("\n" in r["response"] for r in recs)
digits = sum(any(c.isdigit() for c in r["response"]) for r in recs)
print(f"responses with a newline: {multi}   with digits: {digits}")
print("(the paper scorer keeps only the first line and deletes digits, so these inflate its WER)")
