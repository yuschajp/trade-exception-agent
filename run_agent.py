import argparse, json, os, sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data.exception_feed import generate_feed
from agent.exception_agent import TradeExceptionAgent

def print_result(r, verbose=False):
    sev=r.get("severity","?"); err=r.get("error_type","?")
    team=r["routing"]["owning_team"]; fix=r["diagnosis"].get("fix_action","?")
    auto="✅ AUTO" if r["diagnosis"].get("auto_repairable") else "🔴 MANUAL"
    print(f"\n[{sev:8}] {r['exception_id']}")
    print(f"  Error : {err}")
    print(f"  Route : {team}")
    print(f"  Action: {fix}  {auto}")
    if verbose:
        print(f"\n{r['resolution_memo']}")
        print(r['sql_repair'])

def save_results(results, output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    ts=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out=os.path.join(output_dir,f"triage_run_{ts}.json")
    summary={"run_id":ts,"total":len(results),
        "auto_repairable":sum(1 for r in results if r["diagnosis"].get("auto_repairable")),
        "manual_review":sum(1 for r in results if not r["diagnosis"].get("auto_repairable")),
        "by_severity":{s:sum(1 for r in results if r["severity"]==s) for s in ["CRITICAL","HIGH","MEDIUM","LOW"]},
        "results":results}
    with open(out,"w") as f: json.dump(summary,f,indent=2,default=str)
    print(f"\n📁 Results saved → {out}")
    return out, summary

def print_summary(summary):
    print(f"\n{'='*60}\n  TRIAGE SUMMARY — Run {summary['run_id']}\n{'='*60}")
    print(f"  Total      : {summary['total']}")
    print(f"  Auto-repair: {summary['auto_repairable']}")
    print(f"  Manual     : {summary['manual_review']}")
    for sev,count in summary["by_severity"].items():
        if count: print(f"  {sev:10} {'█'*count} ({count})")
    print(f"{'='*60}\n")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=["demo","batch","single","llm"],default="demo")
    parser.add_argument("--n",type=int,default=10)
    parser.add_argument("--verbose",action="store_true")
    args=parser.parse_args()
    use_llm=args.mode=="llm"
    agent=TradeExceptionAgent(use_llm=use_llm)
    if args.mode=="single":
        from data.exception_feed import generate_exception
        print_result(agent.triage_exception(generate_exception(42)),verbose=True)
    else:
        n=args.n if args.mode=="batch" else 10
        feed=generate_feed(n)
        print(f"\nProcessing {n} exceptions... {'(LLM ON)' if use_llm else '(rule-based)'}")
        results=agent.process_batch(feed)
        _,summary=save_results(results)
        for r in results: print_result(r,verbose=args.verbose)
        print_summary(summary)
