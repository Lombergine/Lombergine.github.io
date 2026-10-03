"""Build chser.html (the write-up) from results/summary.json. Charts are inline SVG."""
import json, html

S = json.load(open("results/summary.json"))
P = S["paper"]
SRC = ["MyST", "CMU_Kids", "OGI_Spont", "OGI_Scripted", "OCSC"]
LABEL = {"MyST": "MyST", "CMU_Kids": "CMU Kids", "OGI_Spont": "OGI Spont.",
         "OGI_Scripted": "OGI Scripted", "OCSC": "OCSC"}
CONDS = [("baseline", "Whisper 1-best"), ("onebest", "Claude, 1-best prompt"), ("nbest", "Claude, N-best prompt")]
COL = {"baseline": "var(--c0)", "onebest": "var(--c1)", "nbest": "var(--c2)"}
SAMPLE_N = {"MyST": 150, "CMU_Kids": 100, "OGI_Spont": 100, "OGI_Scripted": 100, "OCSC": 150}
FULL_BASE_OURS = {"All": 30.81, "MyST": 28.24, "CMU_Kids": 18.89, "OGI_Spont": 40.69,
                  "OGI_Scripted": 26.66, "OCSC": 43.70}
B = S["bootstrap_change_vs_baseline"]["paper"]


def tot(c, k):
    return sum(P[c][s][k] for s in SRC)


def bar_chart():
    W, H, left, top, bottom = 680, 300, 44, 16, 56
    gw = (W - left - 10) / len(SRC)
    bw = gw / 4.2
    ymax = 50
    y = lambda v: top + (H - top - bottom) * (1 - v / ymax)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="WER by source and condition">']
    for t in range(0, ymax + 1, 10):
        out.append(f'<line x1="{left}" x2="{W-10}" y1="{y(t):.1f}" y2="{y(t):.1f}" class="grid"/>'
                   f'<text x="{left-6}" y="{y(t)+4:.1f}" class="ax" text-anchor="end">{t}</text>')
    for i, s in enumerate(SRC):
        x0 = left + i * gw + gw * 0.12
        for j, (c, _) in enumerate(CONDS):
            v = P[c][s]["WER"]
            x = x0 + j * bw * 1.05
            out.append(f'<rect x="{x:.1f}" y="{y(v):.1f}" width="{bw:.1f}" height="{y(0)-y(v):.1f}" '
                       f'fill="{COL[c]}" rx="2"><title>{LABEL[s]}: {v:.1f}%</title></rect>'
                       f'<text x="{x+bw/2:.1f}" y="{y(v)-4:.1f}" class="val" text-anchor="middle">{v:.0f}</text>')
        out.append(f'<text x="{x0+1.5*bw*1.05:.1f}" y="{H-bottom+18}" class="ax" text-anchor="middle">{LABEL[s]}</text>')
    out.append(f'<text x="12" y="{top+(H-top-bottom)/2}" class="ax" transform="rotate(-90 12 {top+(H-top-bottom)/2})" text-anchor="middle">WER (%)</text>')
    lx = left
    for c, name in CONDS:
        out.append(f'<rect x="{lx}" y="{H-20}" width="12" height="12" fill="{COL[c]}" rx="2"/>'
                   f'<text x="{lx+17}" y="{H-10}" class="ax">{name}</text>')
        lx += 200
    out.append("</svg>")
    return "".join(out)


def sdi_chart():
    W, H, left = 680, 190, 170
    rows = [(name, c) for c, name in CONDS]
    maxv = max(tot(c, "S") + tot(c, "D") + tot(c, "I") for _, c in rows)
    sc = (W - left - 20) / maxv
    cols = {"S": "var(--s)", "D": "var(--d)", "I": "var(--i)"}
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Error counts by type">']
    for r, (name, c) in enumerate(rows):
        yy = 14 + r * 44
        out.append(f'<text x="{left-8}" y="{yy+18}" class="ax" text-anchor="end">{name}</text>')
        x = left
        for k in "SDI":
            v = tot(c, k)
            out.append(f'<rect x="{x:.1f}" y="{yy}" width="{v*sc:.1f}" height="28" fill="{cols[k]}">'
                       f'<title>{k}: {v}</title></rect>')
            if v * sc > 34:
                out.append(f'<text x="{x+v*sc/2:.1f}" y="{yy+19}" class="inbar" text-anchor="middle">{v}</text>')
            x += v * sc
    lx = left
    for k, name in [("S", "Substitutions"), ("D", "Deletions"), ("I", "Insertions")]:
        out.append(f'<rect x="{lx}" y="{H-18}" width="12" height="12" fill="{cols[k]}" rx="2"/>'
                   f'<text x="{lx+17}" y="{H-8}" class="ax">{name}</text>')
        lx += 140
    out.append("</svg>")
    return "".join(out)


def pct(a, b):
    return 100 * (b - a) / a


rows_t1 = "".join(
    f"<tr><td>{LABEL[s]}</td><td>{S['paper_baseline'][s]:.1f}</td><td>{FULL_BASE_OURS[s]:.1f}</td></tr>"
    for s in SRC) + f"<tr class='tot'><td>All</td><td>{S['paper_baseline']['All']:.1f}</td><td>{FULL_BASE_OURS['All']:.1f}</td></tr>"

rows_t2 = "".join(
    f"<tr><td>{LABEL[s]}</td><td>{SAMPLE_N[s]}</td>" +
    "".join(f"<td>{P[c][s]['WER']:.1f}</td>" for c, _ in CONDS) + "</tr>" for s in SRC)
rows_t2 += ("<tr class='tot'><td>Weighted to full test</td><td>600</td>" +
            "".join(f"<td>{P[c]['weighted_full_test']:.1f}</td>" for c, _ in CONDS) + "</tr>")

rows_t3 = ""
for k, name in [("S", "Substitutions"), ("D", "Deletions"), ("I", "Insertions")]:
    b, o, n = tot("baseline", k), tot("onebest", k), tot("nbest", k)
    rows_t3 += (f"<tr><td>{name}</td><td>{b}</td><td>{o} ({pct(b,o):+.0f}%)</td>"
                f"<td>{n} ({pct(b,n):+.0f}%)</td></tr>")

base_w = P["baseline"]["weighted_full_test"]; nb_w = P["nbest"]["weighted_full_test"]; ob_w = P["onebest"]["weighted_full_test"]
rel = 100 * (base_w - nb_w) / base_w
oov = S["outside_nbest_words"]; ch = S["utterance_changes"]

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zero-Shot Child ASR Correction</title>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#66635c;--rule:#dcd8cf;--card:#ffffff;
--c0:#9a9488;--c1:#d08a3c;--c2:#2f6f8f;--s:#2f6f8f;--d:#7fa9bf;--i:#c4543d;--grid:#e7e3da}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#16171a;--fg:#e9e7e2;--mut:#a29f97;--rule:#33353a;--card:#1d1f23;
--c0:#7c776d;--c1:#e0a05a;--c2:#5aa3c6;--s:#5aa3c6;--d:#9cc3d6;--i:#e07a62;--grid:#2a2c31}}}}
:root[data-theme="dark"]{{--bg:#16171a;--fg:#e9e7e2;--mut:#a29f97;--rule:#33353a;--card:#1d1f23;
--c0:#7c776d;--c1:#e0a05a;--c2:#5aa3c6;--s:#5aa3c6;--d:#9cc3d6;--i:#e07a62;--grid:#2a2c31}}
body{{margin:0;background:var(--bg);color:var(--fg);font:17px/1.62 'Source Serif 4',Georgia,serif}}
main{{max-width:760px;margin:0 auto;padding:48px 16px 80px}}
h1{{font-size:30px;line-height:1.2;margin:0 0 8px;font-weight:600}}
h2{{font:600 15px/1.3 Inter,system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase;margin:44px 0 10px;color:var(--mut)}}
.meta{{font:14px Inter,system-ui,sans-serif;color:var(--mut);margin-bottom:28px}}
.abstract{{background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:18px 20px;font-size:16px}}
.key{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:22px 0}}
.key div{{background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:12px 14px}}
.key b{{display:block;font:600 26px Inter,system-ui,sans-serif}}
.key span{{font:13px Inter,system-ui,sans-serif;color:var(--mut)}}
table{{width:100%;border-collapse:collapse;font:14px Inter,system-ui,sans-serif;margin:12px 0 4px}}
th,td{{text-align:right;padding:6px 8px;border-bottom:1px solid var(--rule)}}
th:first-child,td:first-child{{text-align:left}}
th{{color:var(--mut);font-weight:600}}
tr.tot td{{font-weight:600;border-top:2px solid var(--rule)}}
.cap{{font:13px Inter,system-ui,sans-serif;color:var(--mut);margin:4px 0 18px}}
.tablewrap{{overflow-x:auto}}
svg{{width:100%;height:auto;display:block;margin:10px 0}}
svg .grid{{stroke:var(--grid)}} svg .ax{{font:12px Inter,system-ui,sans-serif;fill:var(--mut)}}
svg .val{{font:11px Inter,system-ui,sans-serif;fill:var(--fg)}} svg .inbar{{font:600 12px Inter,system-ui,sans-serif;fill:#fff}}
pre{{background:var(--card);border:1px solid var(--rule);border-radius:6px;padding:12px;overflow-x:auto;font-size:13px}}
code{{font-size:14px}} a{{color:var(--c2)}}
.ex{{font:13px/1.5 ui-monospace,Menlo,monospace;background:var(--card);border:1px solid var(--rule);border-radius:6px;padding:10px 12px;margin:8px 0}}
.ex span{{color:var(--mut)}}
</style></head><body><main>
<h1>Zero-Shot LLM Correction of Children's Speech Recognition: A Follow-Up on CHSER</h1>
<div class="meta">Aditya Garg · October 2026 · <a href="https://github.com/Lombergine/lombergine.github.io/tree/main/chser-zero-shot">code and outputs</a></div>

<div class="abstract"><b>Abstract.</b> CHSER (Balaji Shankar et al., Interspeech 2025) reports that zero-shot prompting of GPT-4o mini raised word error rate on child speech from 30.5% to 42.1%, which suggests that generative error correction needs fine-tuning or examples. I test whether that holds for a larger model. Using the paper's prompt templates and scoring code, I ran Claude Opus 5.5 zero-shot on a stratified sample of 600 test utterances. With the N-best prompt, the source-weighted WER fell from {base_w:.1f}% to {nb_w:.1f}% (change {B['nbest']['change_pp']:+.1f} points, 95% CI {B['nbest']['ci95'][0]:.1f} to {B['nbest']['ci95'][1]:.1f}), a {rel:.0f}% relative reduction, close to the paper's fine-tuned Flan-T5 result of 21.8%. Without the other hypotheses the gain was small ({B['onebest']['change_pp']:+.1f} points). Insertions were the error type least reduced, which agrees with the paper's error analysis. Most remaining insertions sit at utterance boundaries, concentrated in the OGI spontaneous subset, where the reference and the recognized audio appear to cover different spans. A text-only corrector cannot remove those. The outputs were produced in batches of fifty utterances per model context, so the result should be confirmed with independent API calls before it is treated as settled.</div>

<div class="key">
<div><b>{base_w:.1f}%</b><span>Whisper baseline WER (sample, weighted)</span></div>
<div><b>{nb_w:.1f}%</b><span>after zero-shot N-best correction</span></div>
<div><b>{rel:.0f}%</b><span>relative reduction</span></div>
<div><b>42.1%</b><span>paper: zero-shot GPT-4o mini</span></div>
</div>

<h2>1. Question</h2>
<p>CHSER pairs 200K Whisper-base.en hypotheses with human transcripts from five child speech corpora. Its fine-tuned Flan-T5 corrector reached 21.8% WER on the test split, from a 30.5% baseline. Table 4 of the paper adds an in-context learning experiment: GPT-4o mini scored 42.1% with no examples and 27.3% with one example. The zero-shot condition made transcripts worse.</p>
<p>The question here is narrow. Does zero-shot correction fail because zero-shot correction cannot work on child speech, or because of the model that was tested? A stronger model with the same prompt is the cheapest way to separate the two.</p>

<h2>2. Data and sample</h2>
<p>The released test file (<code>dataset/test/hyp.json</code>, 26,687 utterances) carries five Whisper hypotheses and one reference per utterance but no corpus label. I assumed the file is ordered as in the paper's Table 1 and split it into contiguous blocks of the published sizes. The baseline WER of each block reproduces the published per-corpus baseline to within 0.6 points (Table 1), so the assignment is very likely correct.</p>
<div class="tablewrap"><table><tr><th>Corpus</th><th>Paper baseline</th><th>Recomputed baseline</th></tr>{rows_t1}</table></div>
<p class="cap">Table 1. Baseline WER (%) of Whisper's top hypothesis on the full test split. Recomputed with jiwer on the released file.</p>
<p>I drew 600 utterances without replacement, 150 each from MyST and OCSC and 100 from each other corpus (seed 20261003). Per-corpus WER on the sample is weighted back to the full test split by each corpus's share of reference words, which gives a sample baseline of {base_w:.1f}% against 30.8% on the full split.</p>

<h2>3. Method</h2>
<p>Two prompts were taken verbatim from <code>templates/H2T-LoRA.json</code> in the CHSER repository. The N-best prompt shows the top hypothesis and the four alternatives. The 1-best prompt shows only the top hypothesis. The model was Claude Opus 5.5, with no examples and no fine-tuning, and the reference transcripts were moved out of reach of the model during generation.</p>
<p>Outputs were scored with an exact copy of the paper's normalization from <code>in_context_learning.py</code>. As a check, I also scored them with a second normalization that converts digits to words and splits hyphenated numbers on both sides. The two agree to within 0.15 points, so only the first is reported. Confidence intervals come from a paired bootstrap with 2,000 draws, resampling utterances within each corpus.</p>

<h2>4. Results</h2>
{bar_chart()}
<p class="cap">Figure 1. WER by corpus on the 600-utterance sample.</p>
<div class="tablewrap"><table><tr><th>Corpus</th><th>n</th><th>Whisper</th><th>Claude 1-best</th><th>Claude N-best</th></tr>{rows_t2}</table></div>
<p class="cap">Table 2. WER (%) by corpus, paper normalization. Change against Whisper: 1-best {B['onebest']['change_pp']:+.1f} points (95% CI {B['onebest']['ci95'][0]:.1f} to {B['onebest']['ci95'][1]:.1f}); N-best {B['nbest']['change_pp']:+.1f} points (95% CI {B['nbest']['ci95'][0]:.1f} to {B['nbest']['ci95'][1]:.1f}).</p>
<p>The N-best prompt lowered WER in every corpus. The largest drop was in the OGI spontaneous subset, from {P['baseline']['OGI_Spont']['WER']:.1f}% to {P['nbest']['OGI_Spont']['WER']:.1f}%. OCSC, the conversational CHILDES corpus, improved least in relative terms and remains above 37%.</p>
<p>Almost all of the gain depends on the alternative hypotheses. Shown only the top hypothesis, the model changed {ch['onebest']['changed']} of 600 utterances and lowered WER by {abs(B['onebest']['change_pp']):.1f} points. Shown all five, it changed {ch['nbest']['changed']}, improving {ch['nbest']['better']} and worsening {ch['nbest']['worse']}. It also followed the instruction to draw words from the hypotheses: {oov['nbest']['pct']:.1f}% of its output words appear in none of the five, against {oov['onebest']['pct']:.1f}% under the 1-best prompt.</p>

<h2>5. Error types</h2>
{sdi_chart()}
<p class="cap">Figure 2. Word errors on the sample by type (pooled counts).</p>
<div class="tablewrap"><table><tr><th>Error type</th><th>Whisper</th><th>Claude 1-best</th><th>Claude N-best</th></tr>{rows_t3}</table></div>
<p class="cap">Table 3. Pooled error counts on the sample, with change against Whisper.</p>
<p>Substitutions fell the most. Insertions fell the least, and under the 1-best prompt they did not fall at all. CHSER's error analysis reported the same weakness for its fine-tuned models, which improved substitutions and deletions but struggled with insertions. The pattern therefore seems to belong to the task and the data more than to any one corrector.</p>

<h2>6. Where the insertions are</h2>
<p>I split insertions by position in the alignment. In the Whisper output, 334 of 606 inserted words sit at the very start or end of an utterance. After N-best correction, 316 boundary insertions remain, a drop of 5%, while insertions inside the utterance fell from 272 to 179, a drop of 34%. Just over half of all remaining insertions (258 of 495) come from the OGI spontaneous subset, and 199 of those are at boundaries.</p>
<p>Reading these cases suggests a cause. In OGI spontaneous speech the hypotheses often contain a phrase before or after the span the reference covers, as in the example below. If the audio segment and the reference cover different stretches of a longer monologue, the extra words are real speech that the transcript leaves out, and no model that sees only text can know to delete them.</p>
<div class="ex"><span>REF</span> watch the sunset blue red yellow orange just ... stuff like that<br><span>OUT</span> yeah no that was nice yeah watch the sunset blue red yellow ...</div>
<p>A related floor exists for deletions. OGI spontaneous references transcribe the filled pause <i>uhm</i> 343 times in the full test split, about 2% of reference words, while Whisper's top hypotheses contain filled pauses only 15 times. A text corrector has no evidence of where a pause occurred, so these words stay deleted.</p>

<h2>7. Checks</h2>
<p><b>Memorization.</b> The CHSER test split has been public on GitHub since 2025, so a model could in principle have seen the references. Of the 297 sampled utterances whose reference contains a word found in none of the five hypotheses, the N-best output matched the reference exactly in 9 cases (3%). The model also never produced the CHILDES markers <i>xxx</i> or <i>www</i>, which appear in the references. Neither result points to recall of the test transcripts, though neither rules it out.</p>
<p><b>Computation.</b> WER was recomputed with a separate implementation (editdistance on lowercase tokens, sharing no code with the main script). It gives weighted WERs of 31.3%, 28.8% and 22.9% for the three conditions, each within 0.15 points of Table 2.</p>

<h2>8. Limitations</h2>
<p>The outputs were not generated by independent API calls. They were produced by model instances that each processed a batch of fifty utterances, and each batch came from a single corpus. A model that sees fifty utterances at once can pick up the transcription style of the corpus, such as lowercase text and spelled-out numbers, and that is a mild form of in-context learning. The zero-shot label is therefore approximate. The included <code>run_claude.py</code> sends one request per utterance and is the right way to confirm the result.</p>
<p>The run was done once, at an uncontrolled sampling temperature, on 2.2% of the test split. Claude Opus 5.5 is a much larger model than GPT-4o mini, so this result says nothing about whether the paper's zero-shot number is wrong; the two experiments differ in the model.</p>
<p>One detail of the paper's scorer may matter for its zero-shot number. The normalization deletes every digit and keeps only the first line of a response. A chat model that writes "33" or begins with a sentence such as "Here is the corrected transcription:" followed by a line break would be scored on an empty or wrong string. Whether that affected the GPT-4o mini outputs could be checked directly from the saved responses.</p>

<h2>9. Reproduce</h2>
<pre>pip install jiwer num2words anthropic
python evaluate.py                      # scores the saved outputs (Tables 2 and 3)
export ANTHROPIC_API_KEY=...
python run_claude.py --data sample.json --prompt nbest --out outputs/api_nbest.jsonl
python score_api.py outputs/api_nbest.jsonl</pre>

<h2>Reference</h2>
<p>Balaji Shankar, N., Wang, Z., Zhang, K., Shi, M., and Alwan, A. (2025). CHSER: A dataset and case study on generative speech error correction for child ASR. <i>Proc. Interspeech 2025</i>, 2895. <a href="https://arxiv.org/abs/2505.18463">arXiv:2505.18463</a>. Data and code: <a href="https://github.com/balaji1312/CHSER">github.com/balaji1312/CHSER</a>.</p>
</main></body></html>
"""
open("chser.html", "w").write(page)
print("wrote chser.html", len(page))
