"""Roblox Up-and-Coming top-10 forecaster.

Reads /input/history.ndjson + /input/task.json, writes /output/forecast.json.
Deterministic, stdlib only, no network.

Strategy: the chart moves fast, so persistence loses. We score each game by
recent rank (dominant), plus bounded momentum (climbing), player growth and
stability. For each place we spread probability over the top candidates so a
wrong top guess does not hit the -9.21 floor.
"""
import json, math, os

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

def clip(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def main():
    with open(os.path.join(INPUT_DIR, "task.json")) as f:
        task = json.load(f)
    places = task["places"]
    with open(os.path.join(INPUT_DIR, "history.ndjson")) as f:
        lines = f.read().strip().split("\n")
    reads = [json.loads(ln) for ln in lines if ln.strip()]
    n = len(reads)
    if n == 0:
        raise SystemExit("history.ndjson has no reads; nothing to forecast")
    games = {}
    for idx, rd in enumerate(reads):
        for row in rd.get("up_and_coming") or []:
            uid = row["universe_id"]
            g = games.setdefault(uid, {"ranks": {}, "playing": {}, "name": row.get("name", "")})
            g["ranks"][idx] = row["rank"]
            g["playing"][idx] = row.get("playing") or 0
    W = min(10, n)
    recent = list(range(n - W, n))
    scores = {}
    for uid, g in games.items():
        wsum = 0.0; rsum = 0.0
        for k, idx in enumerate(recent):
            r = g["ranks"].get(idx)
            if r is None:
                continue
            w = 1.5 ** k
            wsum += w; rsum += w * r
        if wsum == 0:
            continue
        avg_rank = rsum / wsum
        half = W // 2
        first = [g["ranks"][i] for i in recent[:half] if i in g["ranks"]]
        second = [g["ranks"][i] for i in recent[half:] if i in g["ranks"]]
        mom = 0.0
        if first and second:
            mom = (sum(first)/len(first)) - (sum(second)/len(second))
        pg = 0.0
        last_p = g["playing"].get(n-1)
        prev_p = None
        for idx in range(n-2, max(n-6, -1), -1):
            if idx in g["playing"] and g["playing"][idx]:
                prev_p = g["playing"][idx]; break
        if last_p and prev_p and prev_p > 0:
            pg = math.log(max(last_p, 1)/prev_p)
        pres = sum(1 for i in recent if g["ranks"].get(i) is not None and g["ranks"][i] <= 20) / W
        # avg_rank dominates; momentum/growth/presence are bounded adjustments
        score = avg_rank - 0.4*clip(mom, -10, 10) - 3.0*clip(pg, -0.3, 0.5) - 2.0*pres
        scores[uid] = score
    ranked = sorted(scores.items(), key=lambda kv: kv[1])
    pool = [uid for uid, _ in ranked[:30]]
    last_read = reads[-1]
    last_rank = {}
    for row in last_read.get("up_and_coming") or []:
        last_rank[row["universe_id"]] = row["rank"]
    probs = []
    for place in range(1, places+1):
        weights = []
        for uid in pool:
            g = games[uid]
            wsum = 0.0; rsum = 0.0
            for k, idx in enumerate(recent):
                r = g["ranks"].get(idx)
                if r is None: continue
                w = 1.5 ** k; wsum += w; rsum += w*r
            exp_rank = (rsum/wsum) if wsum else 25.0
            spread = 1.5 + 0.35*place
            d = abs(exp_rank - place)
            wgt = math.exp(-(d*d)/(2*spread*spread))
            lr = last_rank.get(uid)
            if lr is not None:
                d2 = abs(lr - place)
                wgt += 0.6*math.exp(-(d2*d2)/(2*spread*spread))
            weights.append((uid, wgt))
        tot = sum(w for _, w in weights)
        if tot <= 0:
            continue
        weights.sort(key=lambda x: -x[1])
        chosen = weights[:12]
        s = sum(w for _, w in chosen)
        for uid, w in chosen:
            p = 0.85 * (w / s)
            if p > 0.45: p = 0.45
            probs.append({"universe_id": int(uid), "place": place, "p": round(p, 4)})
    top10 = [int(uid) for uid, _ in ranked[:10]]
    if len(top10) < 10:
        for uid in pool:
            if int(uid) not in top10:
                top10.append(int(uid))
            if len(top10) == 10: break
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out = os.path.join(OUTPUT_DIR, task.get("output", "forecast.json"))
    with open(out, "w", encoding="utf-8") as f:
        f.write(json.dumps({"probabilities": probs, "top10": top10}) + "\n")
    print("wrote", out, "probs:", len(probs), "top10:", top10)

if __name__ == "__main__":
    main()
