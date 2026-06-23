import random, uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict

COUNTERPARTIES = {
    "GOLDMAN_SACHS":"GSFOOBAR123456789012","JP_MORGAN":"JPMORG00001234567890",
    "CITADEL":"CITADL00009876543210","MILLENNIUM":"MLMGMT00001111222233",
    "SCHONFELD":"SCHON000002222233334","BARCLAYS":"BARCLY00005678901234",
}
SECURITIES = {
    "EQ":["AAPL","MSFT","JPM","GS","BAC","TSLA","NVDA"],
    "FI":["US10Y","US2Y","CORP_IG_001","CORP_HY_002","MBS_001"],
    "FX":["EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD"],
    "FUT":["ESZ4","NQZ4","CLF5","GCG5","ZNZ4"],
    "OTC":["IRS_USD_10Y","CDS_IG_5Y","FX_FWD_EURUSD_3M"],
}
VALID_CURRENCIES = ["USD","EUR","GBP","JPY","CAD","AUD","CHF"]
EXCEPTION_TYPES = [
    {"error_type":"INVALID_CURRENCY","category":"Static Data","severity":"HIGH","owning_team":"Middle Office - Static Data","sla_hours":2},
    {"error_type":"MISMATCHED_BROKER_LEI","category":"Counterparty Data","severity":"HIGH","owning_team":"Middle Office - Counterparty","sla_hours":4},
    {"error_type":"SETTLEMENT_FAIL","category":"Settlement","severity":"CRITICAL","owning_team":"Operations - Settlement","sla_hours":1},
    {"error_type":"PRICE_TOLERANCE_BREACH","category":"Pricing","severity":"MEDIUM","owning_team":"Middle Office - Pricing","sla_hours":4},
    {"error_type":"MISSING_UTI","category":"Regulatory Reporting","severity":"HIGH","owning_team":"Operations - RegReporting","sla_hours":2},
    {"error_type":"MARGIN_CALL_DISPUTE","category":"Margin & Collateral","severity":"CRITICAL","owning_team":"Middle Office - Margin","sla_hours":1},
    {"error_type":"DUPLICATE_TRADE","category":"Booking","severity":"HIGH","owning_team":"Middle Office - Trade Capture","sla_hours":2},
    {"error_type":"SECURITY_NOT_FOUND","category":"Static Data","severity":"HIGH","owning_team":"Middle Office - Static Data","sla_hours":3},
    {"error_type":"CONFIRMATION_MISMATCH","category":"Confirmation","severity":"MEDIUM","owning_team":"Middle Office - Confirmations","sla_hours":6},
    {"error_type":"NOSTRO_BREAK","category":"Reconciliation","severity":"HIGH","owning_team":"Operations - Reconciliation","sla_hours":4},
]

def generate_exception(seed_offset=0):
    random.seed(seed_offset + hash(str(datetime.now())) % 10000)
    tmpl=random.choice(EXCEPTION_TYPES)
    ac=random.choice(["EQ","FI","FX","FUT","OTC"])
    ctpy=random.choice(list(COUNTERPARTIES.keys()))
    security=random.choice(SECURITIES[ac])
    currency=random.choice(VALID_CURRENCIES)
    trade_date=datetime.now(timezone.utc)-timedelta(hours=random.randint(0,48))
    payload={
        "trade_id":f"TRD-{datetime.now().strftime('%Y')}-{random.randint(1000,9999)}",
        "asset_class":ac,"security":security,"quantity":round(random.uniform(100,50000),0),
        "price":round(random.uniform(10,500),4),"notional_usd":round(random.uniform(10000,5000000),2),
        "counterparty":ctpy,"broker_lei":COUNTERPARTIES[ctpy],"currency":currency,
        "trade_date":trade_date.isoformat(),
        "settle_date":(trade_date+timedelta(days=2)).isoformat(),
        "trader":f"TRADER_{random.randint(1,20):02d}",
        "book":f"BOOK_{ac}_{random.randint(1,5)}",
        "source_system":random.choice(["MUREX","ALADDIN","BLOOMBERG","INTERNAL_OMS"]),
    }
    et=tmpl["error_type"]
    if et=="INVALID_CURRENCY": payload["currency"]=random.choice(["XYZ","ZZZ","AAA","999"])
    elif et=="MISMATCHED_BROKER_LEI": payload["broker_lei"]="BADLEI"+str(random.randint(10000,99999))
    elif et=="MISSING_UTI": payload["uti"]=None; payload["asset_class"]="OTC"
    elif et=="PRICE_TOLERANCE_BREACH": payload["mid_price"]=round(payload["price"]*0.9,4); payload["price"]=round(payload["price"]*1.15,4)
    elif et=="MARGIN_CALL_DISPUTE": payload["our_margin_call"]=round(random.uniform(100000,2000000),2); payload["ctpy_margin_call"]=round(payload["our_margin_call"]*random.uniform(0.8,1.2),2)
    elif et=="DUPLICATE_TRADE": payload["duplicate_of"]=f"TRD-{datetime.now().strftime('%Y')}-{random.randint(1000,9999)}"
    elif et=="SECURITY_NOT_FOUND": payload["security"]=f"UNKNOWN_{random.randint(1000,9999)}"
    elif et=="NOSTRO_BREAK": payload["ledger_balance"]=round(random.uniform(1000000,10000000),2); payload["nostro_balance"]=round(payload["ledger_balance"]*random.uniform(0.95,1.05),2); payload["break_amount"]=round(abs(payload["ledger_balance"]-payload["nostro_balance"]),2)
    return {
        "exception_id":f"EXC-{uuid.uuid4().hex[:8].upper()}",
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "sla_deadline":(datetime.now(timezone.utc)+timedelta(hours=tmpl["sla_hours"])).isoformat(),
        "sla_hours":tmpl["sla_hours"],"error_type":et,"category":tmpl["category"],
        "severity":tmpl["severity"],"owning_team":tmpl["owning_team"],
        "description":f"Exception: {et}","status":"OPEN","trade_payload":payload,
    }

def generate_feed(n=20):
    return [generate_exception(i) for i in range(n)]

if __name__=="__main__":
    for e in generate_feed(5):
        print(f"[{e['severity']:8}] {e['error_type']:30} | {e['trade_payload']['asset_class']} | {e['exception_id']}")
