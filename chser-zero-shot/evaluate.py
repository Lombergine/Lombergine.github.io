"""Score zero-shot LLM correction on a stratified CHSER test sample.

Two normalizations are reported:
  paper : an exact copy of the normalization in CHSER's
          code/gensec/in_context_learning/in_context_learning.py
  fair  : lowercase, digits to words, hyphens split, punctuation removed,
          common contractions expanded. Applied to references and hypotheses alike.

Outputs results/summary.json, results/per_utterance.csv and results/tables.md.
"""
import json, re, csv, random, collections
import jiwer
from num2words import num2words

random.seed(0)
SOURCES = ["MyST", "CMU_Kids", "OGI_Spont", "OGI_Scripted", "OCSC"]
# Reference word counts per source over the FULL CHSER test split (26,687 utterances).
# Used to weight per-source WER back to the full test composition.
FULL_REF_WORDS = {"MyST": 202215, "CMU_Kids": 6019, "OGI_Spont": 17955,
                  "OGI_Scripted": 37656, "OCSC": 44256}
PAPER_BASELINE = {"All": 30.5, "MyST": 28.1, "CMU_Kids": 18.7, "OGI_Spont": 40.6,
                  "OGI_Scripted": 26.2, "OCSC": 43.1}


def paper_norm_pred(x):
    x = re.sub("</s>", "", x).lower()
    x = re.sub(r"[^\w\s]|[\d]", "", x)
    x = re.sub(r"\n+.+", "", x)
    return x


def paper_norm_ref(x):
    return re.sub(r"[^\w\s]|[\d]", "", x)


CONTRACTIONS = {"it's": "it is", "that's": "that is", "i'm": "i am", "don't": "do not",
                "doesn't": "does not", "didn't": "did not", "can't": "can not",
                "won't": "will not", "isn't": "is not", "there's": "there is",
                "they're": "they are", "we're": "we are", "you're": "you are",
                "i've": "i have", "let's": "let us", "what's": "what is",
                "he's": "he is", "she's": "she is", "wasn't": "was not",
                "aren't": "are not", "i'll": "i will", "i'd": "i would"}


def fair_norm(x):
    x = x.lower().replace("</s>", " ")
    x = " ".join(CONTRACTIONS.get(t, t) for t in x.split())
    x = re.sub(r"\d+", lambda m: " " + num2words(int(m.group())) + " ", x)
    x = x.replace("-", " ")
    x = re.sub(r"[^a-z\s]", "", x)
    return " ".join(x.split())


def counts(refs, hyps):
    o = jiwer.process_words(refs, hyps)
    n = o.substitutions + o.deletions + o.hits
    return dict(S=o.substitutions, D=o.deletions, I=o.insertions, N=n)


def wer(c):
    return 100 * (c["S"] + c["D"] + c["I"]) / c["N"]


def weighted_wer(per_source):
    tot = sum(FULL_REF_WORDS.values())
    return sum(per_source[s] * FULL_REF_WORDS[s] / tot for s in SOURCES)


def boot_diff(items, key_a, key_b, norm, B=2000):
    """Paired bootstrap of WER(b) - WER(a), resampling utterances within each source,
    then combining with full-test weights. Returns (point, lo, hi)."""
    by = collections.defaultdict(list)
    for it in items:
        ref = norm(it["ref"]) if norm is fair_norm else paper_norm_ref(it["ref"])
        def n(h, k):
            if norm is fair_norm:
                return fair_norm(h)
            return paper_norm_ref(h) if k == "baseline" else paper_norm_pred(h)
        ca = counts([ref], [n(it[key_a], key_a)]); cb = counts([ref], [n(it[key_b], key_b)])
        by[it["source"]].append((ca, cb))
    def stat(sample):
        wa, wb = {}, {}
        for s in SOURCES:
            A = [0, 0]; Bc = [0, 0]
            for ca, cb in sample[s]:
                A[0] += ca["S"] + ca["D"] + ca["I"]; A[1] += ca["N"]
                Bc[0] += cb["S"] + cb["D"] + cb["I"]; Bc[1] += cb["N"]
            wa[s] = 100 * A[0] / A[1]; wb[s] = 100 * Bc[0] / Bc[1]
        return weighted_wer(wb) - weighted_wer(wa)
    point = stat(by)
    draws = []
    for _ in range(B):
        draws.append(stat({s: [random.choice(by[s]) for _ in by[s]] for s in SOURCES}))
    draws.sort()
    return point, draws[int(0.025 * B)], draws[int(0.975 * B)]


def main():
    sample = json.load(open("sample.json"))
    nbest = json.load(open("outputs/nbest_all.json"))
    onebest = json.load(open("outputs/1best_all.json"))
    items = [dict(uid=s["uid"], source=s["source"], ref=s["output"], hyps=s["input"],
                  baseline=s["input"][0], nbest=nbest[s["uid"]], onebest=onebest[s["uid"]])
             for s in sample]

    conds = ["baseline", "onebest", "nbest"]
    summary = {}
    for normname in ["paper", "fair"]:
        res = {}
        for c in conds:
            per = {}
            for s in SOURCES + ["sample_pooled"]:
                sub = items if s == "sample_pooled" else [i for i in items if i["source"] == s]
                if normname == "paper":
                    refs = [paper_norm_ref(i["ref"]) for i in sub]
                    hyps = [paper_norm_ref(i[c]) if c == "baseline" else paper_norm_pred(i[c]) for i in sub]
                else:
                    refs = [fair_norm(i["ref"]) for i in sub]
                    hyps = [fair_norm(i[c]) for i in sub]
                k = counts(refs, hyps)
                per[s] = dict(k, WER=round(wer(k), 2))
            per["weighted_full_test"] = round(weighted_wer({s: per[s]["WER"] for s in SOURCES}), 2)
            res[c] = per
        summary[normname] = res

    # paired bootstrap CIs on the weighted change vs baseline
    summary["bootstrap_change_vs_baseline"] = {}
    for normname, norm in [("paper", paper_norm_pred), ("fair", fair_norm)]:
        summary["bootstrap_change_vs_baseline"][normname] = {}
        for c in ["onebest", "nbest"]:
            p, lo, hi = boot_diff(items, "baseline", c, norm)
            summary["bootstrap_change_vs_baseline"][normname][c] = dict(
                change_pp=round(p, 2), ci95=[round(lo, 2), round(hi, 2)])

    # out-of-hypothesis words: words in the correction that appear in none of the 5 hypotheses
    oov = {}
    for c in ["onebest", "nbest"]:
        total = new = new_in_ref = 0
        for i in items:
            pool = set(w for h in i["hyps"] for w in fair_norm(h).split())
            refw = set(fair_norm(i["ref"]).split())
            for w in fair_norm(i[c]).split():
                total += 1
                if w not in pool:
                    new += 1
                    new_in_ref += w in refw
        oov[c] = dict(words=total, outside_nbest=new, pct=round(100 * new / total, 2),
                      of_which_in_reference=new_in_ref)
    summary["outside_nbest_words"] = oov

    # how often each condition changed the utterance, and whether the change helped
    changes = {}
    for c in ["onebest", "nbest"]:
        changed = better = worse = 0
        for i in items:
            r = fair_norm(i["ref"]); b = fair_norm(i["baseline"]); h = fair_norm(i[c])
            if h != b:
                changed += 1
                eb = jiwer.wer(r, b) if r else 0; eh = jiwer.wer(r, h) if r else 0
                better += eh < eb; worse += eh > eb
        changes[c] = dict(changed=changed, better=better, worse=worse, n=len(items))
    summary["utterance_changes"] = changes
    summary["paper_baseline"] = PAPER_BASELINE
    summary["paper_gpt4o_mini"] = {"zero_shot": 42.1, "one_shot": 27.3, "five_shot": 27.4}
    summary["paper_finetuned"] = {"flan_t5": 21.8, "llama": 24.8, "nbest_oracle": 17.7}

    import os
    os.makedirs("results", exist_ok=True)
    json.dump(summary, open("results/summary.json", "w"), indent=1)

    with open("results/per_utterance.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["uid", "source", "reference", "whisper_best", "claude_1best", "claude_nbest",
                    "wer_baseline", "wer_1best", "wer_nbest"])
        for i in items:
            r = fair_norm(i["ref"])
            w.writerow([i["uid"], i["source"], i["ref"], i["baseline"], i["onebest"], i["nbest"],
                        round(jiwer.wer(r, fair_norm(i["baseline"])), 3),
                        round(jiwer.wer(r, fair_norm(i["onebest"])), 3),
                        round(jiwer.wer(r, fair_norm(i["nbest"])), 3)])
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
