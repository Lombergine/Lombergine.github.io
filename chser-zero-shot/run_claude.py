"""Zero-shot generative error correction on CHSER with the Claude API.

Each utterance is sent as its own request, using the exact prompt templates from
CHSER (code/gensec/in_context_learning/templates/H2T-LoRA.json).

Usage
  pip install anthropic jiwer num2words
  export ANTHROPIC_API_KEY=...
  # the 600-utterance sample used in the write-up
  python run_claude.py --data sample.json --prompt nbest --out outputs/api_nbest.jsonl
  # the full CHSER test split (26,687 utterances; check cost first)
  python run_claude.py --data data_test/hyp.json --prompt nbest --out outputs/api_full_nbest.jsonl

The script resumes: utterances already in --out are skipped.
"""
import argparse, json, os, re, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic

NBEST = ("Below is the best-hypotheses transcribed from speech recognition system. Please try to "
         "revise it using the words which are only included into other-hypothesis, and write the "
         "response for the true transcription.\n\n### Best-hypothesis:\n{best}\n\n"
         "### Other-hypothesis:\n{others}\n\n### Response:\n")
ONEBEST = ("Below is the best-hypotheses transcribed from speech recognition system. Please try to "
           "revise it and write the response for the true transcription.\n\n"
           "### Best-hypothesis:\n{best}\n\n### Response:\n")


def build_prompt(item, kind):
    hyps = item["input"]
    if kind == "nbest":
        return NBEST.format(best=hyps[0], others=hyps[1:])
    return ONEBEST.format(best=hyps[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--prompt", choices=["nbest", "1best"], default="nbest")
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--temperature", type=float, default=0.0,
                    help="CHSER used 0.7 for GPT-4o mini; 0.0 is easier to reproduce")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    data = json.load(open(args.data))
    for k, it in enumerate(data):
        it.setdefault("uid", it.get("id", f"t{k:05d}"))
    if args.limit:
        data = data[: args.limit]

    done = set()
    if os.path.exists(args.out):
        for line in open(args.out):
            done.add(json.loads(line)["uid"])
    todo = [it for it in data if it["uid"] not in done]
    print(f"{len(done)} already done, {len(todo)} to run with {args.model}")

    client = anthropic.Anthropic()
    lock = threading.Lock()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    fout = open(args.out, "a")

    def call(it):
        prompt = build_prompt(it, args.prompt)
        for attempt in range(6):
            try:
                msg = client.messages.create(
                    model=args.model, max_tokens=1024, temperature=args.temperature,
                    messages=[{"role": "user", "content": prompt}])
                text = "".join(b.text for b in msg.content if b.type == "text")
                return dict(uid=it["uid"], response=text, reference=it["output"],
                            best=it["input"][0], model=args.model, prompt=args.prompt,
                            temperature=args.temperature)
            except (anthropic.RateLimitError, anthropic.APIConnectionError,
                    anthropic.InternalServerError):
                time.sleep(2 ** attempt)
        raise RuntimeError(f"failed on {it['uid']}")

    with ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(call, it) for it in todo]
        for n, f in enumerate(as_completed(futs), 1):
            rec = f.result()
            with lock:
                fout.write(json.dumps(rec) + "\n"); fout.flush()
            if n % 100 == 0:
                print(f"{n}/{len(todo)}")
    fout.close()
    print("done; score with: python score_api.py", args.out)


if __name__ == "__main__":
    main()
