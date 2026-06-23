import json, os, uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

STATIC_REFERENCE = {
    "LEI_MAP": {
        "GOLDMAN_SACHS":"GSFOOBAR123456789012","JP_MORGAN":"JPMORG00001234567890",
        "CITADEL":"CITADL00009876543210","MILLENNIUM":"MLMGMT00001111222233",
        "SCHONFELD":"SCHON000002222233334","BARCLAYS":"BARCLY00005678901234",
    },
    "VALID_CURRENCIES":["USD","EUR","GBP","JPY","CAD","AUD","CHF"],
    "SECURITY_MASTER":["AAPL","MSFT","JPM","GS","US10Y","US2Y","CORP_IG_001","MBS_001","EUR/USD","ESZ4","IRS_USD_10Y"],
    "PRICE_TOLERANCE_PCT":0.03,"MARGIN_DISPUTE_THRESHOLD_PCT":0.02,
}
TEAM_ROUTING = {
    "Static Data":"Middle Office — Static Data","Counterparty Data":"Middle Office — Counterparty",
    "Settlement":"Operations — Settlement","Pricing":"Middle Office — Pricing",
    "Regulatory Reporting":"Operations — Reg Reporting","Margin & Collateral":"Middle Office — Margin",
    "Booking":"Middle Office — Trade Capture","Confirmation":"Middle Office — Confirmations",
    "Reconciliation":"Operations — Reconciliation",
}
SEVERITY_PRIORITY = {"CRITICAL":1,"HIGH":2,"MEDIUM":3,"LOW":4}

class ReferenceDataTool:
    def get_lei(self,ctpy): return STATIC_REFERENCE["LEI_MAP"].get(ctpy)
    def get_valid_currencies(self): return STATIC_REFERENCE["VALID_CURRENCIES"]
    def get_security_master(self): return STATIC_REFERENCE["SECURITY_MASTER"]
    def validate_price(self,price,mid):
        dev=abs(price-mid)/mid if mid else 0
        tol=STATIC_REFERENCE["PRICE_TOLERANCE_PCT"]
        return {"within_tolerance":dev<=tol,"deviation_pct":round(dev*100,4)}
    def validate_margin(self,our,ctpy):
        dev=abs(our-ctpy)/our if our else 0
        tol=STATIC_REFERENCE["MARGIN_DISPUTE_THRESHOLD_PCT"]
        return {"within_threshold":dev<=tol,"dispute_amount":round(abs(our-ctpy),2),"deviation_pct":round(dev*100,4)}

class TradeExceptionAgent:
    def __init__(self,use_llm=True):
        self.static_reference_data=STATIC_REFERENCE
        self.ref=ReferenceDataTool()
        self.use_llm=use_llm and bool(os.environ.get("ANTHROPIC_API_KEY"))
        self.audit_trail=[]

    def fetch_mcp_reference_data(self,lookup_key,entity_name=None):
        if lookup_key=="LEI": return self.ref.get_lei(entity_name)
        elif lookup_key=="CCY": return self.ref.get_valid_currencies()
        elif lookup_key=="SECURITIES": return self.ref.get_security_master()
        return None

    def triage_exception(self,exception):
        if isinstance(exception,str):
            import json as _j
            try: exception=_j.loads(exception)
            except: return {"status":"REJECTED","reason":"Malformed JSON"}
        exc_id=exception.get("exception_id",f"EXC-{uuid.uuid4().hex[:8].upper()}")
        et=exception.get("error_type","UNKNOWN")
        severity=exception.get("severity","MEDIUM")
        category=exception.get("category","Unknown")
        trade=exception.get("trade_payload",exception)
        diagnosis=self._diagnose(et,trade,exception)
        llm=self._llm_enrich(exception,diagnosis) if self.use_llm else None
        routing=self._route(category,severity,exception)
        memo=self._generate_memo(exc_id,et,trade,diagnosis,routing,llm)
        sql=self.generate_sql_repair({"trade_id":trade.get("trade_id","UNKNOWN"),"error_type":et,**diagnosis})
        result={"exception_id":exc_id,"triaged_at":datetime.now(timezone.utc).isoformat(),
            "error_type":et,"severity":severity,"category":category,"status":"TRIAGED",
            "diagnosis":diagnosis,"routing":routing,"resolution_memo":memo,"sql_repair":sql,"llm_analysis":llm,
            "audit_entry":{"exception_id":exc_id,"action":"TRIAGED","agent":"TradeExceptionAgent_v2",
                "timestamp":datetime.now(timezone.utc).isoformat()}}
        self.audit_trail.append(result["audit_entry"])
        return result

    def _diagnose(self,et,trade,exception):
        d={"root_cause":et,"fields_affected":[],"fix_action":"MANUAL_REVIEW","auto_repairable":False}
        if et=="INVALID_CURRENCY":
            d.update({"fields_affected":["currency"],"bad_value":trade.get("currency"),"suggested_fix":"USD","fix_action":"UPDATE_CURRENCY","auto_repairable":True})
        elif et=="MISMATCHED_BROKER_LEI":
            correct=self.ref.get_lei(trade.get("counterparty"))
            d.update({"fields_affected":["broker_lei"],"bad_value":trade.get("broker_lei"),"correct_value":correct,"fix_action":"UPDATE_LEI","suggested_fix":correct,"auto_repairable":bool(correct)})
        elif et=="SETTLEMENT_FAIL":
            d.update({"fields_affected":["settlement_status"],"fix_action":"CONTACT_CUSTODIAN","escalation":"Contact custodian within 1hr"})
        elif et=="PRICE_TOLERANCE_BREACH":
            price=trade.get("price",0); mid=trade.get("mid_price",price*0.95)
            chk=self.ref.validate_price(price,mid)
            d.update({"fields_affected":["price"],"bad_value":price,"mid_price":mid,"deviation_pct":chk["deviation_pct"],"fix_action":"PRICE_CHALLENGE"})
        elif et=="MISSING_UTI":
            d.update({"fields_affected":["uti"],"fix_action":"GENERATE_UTI","suggested_fix":f"UTI-{uuid.uuid4().hex[:16].upper()}","auto_repairable":True,"regulatory_note":"CFTC Part 43/45 required"})
        elif et=="MARGIN_CALL_DISPUTE":
            our=trade.get("our_margin_call",0); ctpy=trade.get("ctpy_margin_call",0)
            chk=self.ref.validate_margin(our,ctpy)
            d.update({"fields_affected":["margin_call"],"our_calculation":our,"ctpy_calculation":ctpy,"dispute_amount":chk["dispute_amount"],"fix_action":"ESCALATE_TO_SENIOR" if chk["dispute_amount"]>500000 else "SEND_DISPUTE_NOTICE"})
        elif et=="DUPLICATE_TRADE":
            d.update({"fields_affected":["trade_id"],"duplicate_of":trade.get("duplicate_of"),"fix_action":"CANCEL_DUPLICATE","escalation":"Requires trader confirmation"})
        elif et=="SECURITY_NOT_FOUND":
            d.update({"fields_affected":["security"],"bad_value":trade.get("security"),"fix_action":"ADD_TO_SECURITY_MASTER","escalation":"Static data team must onboard security"})
        elif et=="CONFIRMATION_MISMATCH":
            d.update({"fields_affected":["trade_terms"],"fix_action":"SEND_AMENDED_CONFIRMATION"})
        elif et=="NOSTRO_BREAK":
            d.update({"fields_affected":["cash_position"],"break_amount":trade.get("break_amount",0),"fix_action":"ESCALATE_TO_SENIOR" if trade.get("break_amount",0)>100000 else "INVESTIGATE_BREAK"})
        return d

    def _route(self,category,severity,exception):
        return {"owning_team":TEAM_ROUTING.get(category,"Middle Office — General"),
            "priority":SEVERITY_PRIORITY.get(severity,4),"severity":severity,
            "sla_deadline":exception.get("sla_deadline"),"sla_hours":exception.get("sla_hours"),
            "escalate_to":"Head of Middle Office" if severity=="CRITICAL" else None}

    def _llm_enrich(self,exception,diagnosis):
        try:
            import anthropic
            client=anthropic.Anthropic()
            prompt=f"""You are a senior capital markets middle office analyst. Analyze this trade exception and respond in JSON with keys: explanation (2-3 sentences), risk_assessment (1 sentence), next_steps (list of 3), estimated_resolution_minutes (int).

Exception: {json.dumps(exception,default=str)}
Diagnosis: {json.dumps(diagnosis,default=str)}"""
            msg=client.messages.create(model="claude-sonnet-4-6",max_tokens=500,messages=[{"role":"user","content":prompt}])
            raw=msg.content[0].text.strip()
            if raw.startswith("```"): raw=raw.split("```")[1]; raw=raw[4:] if raw.startswith("json") else raw
            return json.loads(raw.strip())
        except Exception as e:
            return {"error":str(e),"fallback":"Rule-based triage used"}

    def _generate_memo(self,exc_id,et,trade,diagnosis,routing,llm):
        ts=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        llm_sec=""
        if llm and "explanation" in llm:
            llm_sec=f"\nAI ANALYSIS\n───────────\n{llm.get('explanation','')}\n\nRisk: {llm.get('risk_assessment','')}\n\nNext Steps:\n"+"\n".join("• "+s for s in llm.get("next_steps",[]))
        return f"""╔══════════════════════════════════════════════════════════════╗
║         TRADE EXCEPTION RESOLUTION MEMO                      ║
╚══════════════════════════════════════════════════════════════╝
Exception ID : {exc_id}
Trade ID     : {trade.get('trade_id','UNKNOWN')}
Generated    : {ts}
Severity     : {routing.get('severity')}
Error Type   : {et}
Owning Team  : {routing.get('owning_team')}
SLA          : {routing.get('sla_hours')} hours

TRADE DETAILS
─────────────
Asset Class  : {trade.get('asset_class','N/A')}
Security     : {trade.get('security','N/A')}
Counterparty : {trade.get('counterparty','N/A')}
Notional     : ${trade.get('notional_usd',0):,.2f}
Currency     : {trade.get('currency','N/A')}
Source System: {trade.get('source_system','N/A')}

DIAGNOSIS
─────────
Root Cause   : {diagnosis.get('root_cause')}
Fields       : {', '.join(diagnosis.get('fields_affected',[]))}
Fix Action   : {diagnosis.get('fix_action')}
Auto-Repair  : {'Yes' if diagnosis.get('auto_repairable') else 'No — manual intervention required'}
{('Suggested Fix: '+str(diagnosis.get('suggested_fix'))) if diagnosis.get('suggested_fix') else ''}
{('Escalation: '+str(diagnosis.get('escalation'))) if diagnosis.get('escalation') else ''}
{llm_sec}
═══════════════════════════════════════════════════════════════
END OF MEMO — {exc_id}
═══════════════════════════════════════════════════════════════""".strip()

    def generate_sql_repair(self,analysis):
        tid=analysis.get("trade_id","UNKNOWN"); et=analysis.get("error_type","UNKNOWN")
        ts=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        hdr=f"-- EXCEPTION AGENT v2 — {et} — {tid} — {ts}"
        if et=="INVALID_CURRENCY":
            fix=analysis.get("suggested_fix","USD")
            return f"{hdr}\nUPDATE trade_ledger SET currency='{fix}',operational_status='STP_READY',last_modified_by='EXCEPTION_AGENT_V2' WHERE trade_id='{tid}';\nINSERT INTO exception_audit_log(trade_id,error_type,action,resolved_by) VALUES('{tid}','{et}','AUTO_REPAIRED','EXCEPTION_AGENT_V2');"
        elif et=="MISMATCHED_BROKER_LEI":
            fix=analysis.get("correct_value") or analysis.get("suggested_fix","UNKNOWN")
            return f"{hdr}\nUPDATE trade_ledger SET broker_lei='{fix}',operational_status='STP_READY',last_modified_by='EXCEPTION_AGENT_V2' WHERE trade_id='{tid}';\nINSERT INTO exception_audit_log(trade_id,error_type,action,resolved_by) VALUES('{tid}','{et}','AUTO_REPAIRED','EXCEPTION_AGENT_V2');"
        elif et=="MISSING_UTI":
            uti=analysis.get("suggested_fix",f"UTI-{uuid.uuid4().hex[:16].upper()}")
            return f"{hdr}\nUPDATE trade_ledger SET uti='{uti}',reg_reporting_status='PENDING_SUBMISSION',last_modified_by='EXCEPTION_AGENT_V2' WHERE trade_id='{tid}';\nINSERT INTO reg_reporting_queue(trade_id,uti,report_type,status) VALUES('{tid}','{uti}','CFTC_PART45','QUEUED');"
        else:
            return f"{hdr}\n-- No automated repair for {et} — manual review required\nINSERT INTO exception_audit_log(trade_id,error_type,action,resolved_by) VALUES('{tid}','{et}','ROUTED_FOR_MANUAL_REVIEW','EXCEPTION_AGENT_V2');"

    def process_batch(self,exceptions):
        return [self.triage_exception(e) for e in sorted(exceptions,key=lambda e:SEVERITY_PRIORITY.get(e.get("severity","LOW"),4))]

if __name__=="__main__":
    import sys; sys.path.insert(0,".")
    from data.exception_feed import generate_feed
    agent=TradeExceptionAgent(use_llm=False)
    results=agent.process_batch(generate_feed(5))
    for r in results:
        print(f"[{r['severity']:8}] {r['error_type']:30} → {r['routing']['owning_team']}")
        print(f"  Fix: {r['diagnosis'].get('fix_action')}  Auto: {r['diagnosis'].get('auto_repairable',False)}")
