import json
from datetime import datetime

class TradeExceptionAgent:
    def __init__(self):
        # Simulated Middle-Office Static Reference Data (The Agent's "Source of Truth")
        self.static_reference_data = {
            "LEI_MAP": {
                "GOLDMAN_SACHS": "GSFOOBAR123456789012",
                "MILLENNIUM": "MLMGMT00001111222233",
                "SCHONFELD": "SCHON000002222233334"
            },
            "VALID_CURRENCIES": ["USD", "EUR", "GBP", "JPY", "CAD"],
            "SECURITY_MASTER": ["AAPL", "MSFT", "JPM", "US10Y_BOND", "CORP_BOND"]
        }

    def fetch_mcp_reference_data(self, lookup_key, entity_name=None):
        """Simulates a Model Context Protocol (MCP) tool call fetching system reference data."""
        if lookup_key == "LEI" and entity_name in self.static_reference_data["LEI_MAP"]:
            return self.static_reference_data["LEI_MAP"][entity_name]
        elif lookup_key == "CCY":
            return self.static_reference_data["VALID_CURRENCIES"]
        elif lookup_key == "SECURITIES":
            return self.static_reference_data["SECURITY_MASTER"]
        return None

    def triage_exception(self, raw_payload):
        """Parses broken JSON payloads and diagnoses the root cause of the break."""
        try:
            trade = json.loads(raw_payload)
        except json.JSONDecodeError:
            return {"status": "REJECTED", "reason": "Malformed JSON Payload", "action": "Reject Payload"}

        trade_id = trade.get("trade_id", "UNKNOWN")
        currency = trade.get("currency")
        broker = trade.get("counterparty")
        security = trade.get("security")
        lei = trade.get("broker_lei")

        # Diagnosis Pipeline
        if currency not in self.fetch_mcp_reference_data("CCY"):
            return {
                "trade_id": trade_id,
                "error_type": "INVALID_CURRENCY",
                "field": "currency",
                "bad_value": currency,
                "fix_suggestion": "USD"
            }
            
        expected_lei = self.fetch_mcp_reference_data("LEI", broker)
        if lei != expected_lei:
            return {
                "trade_id": trade_id,
                "error_type": "MISMATCHED_BROKER_LEI",
                "field": "broker_lei",
                "bad_value": lei,
                "correct_value": expected_lei,
                "fix_suggestion": f"Update LEI to {expected_lei}"
            }

        return {"trade_id": trade_id, "error_type": "NONE", "status": "STP_READY"}

    def generate_sql_repair(self, analysis):
        """Generates an institutional-grade SQL repair script based on agent diagnosis."""
        trade_id = analysis.get("trade_id")
        error_type = analysis.get("error_type")
        
        if error_type == "MISMATCHED_BROKER_LEI":
            correct_lei = analysis.get("correct_value")
            sql_script = f"""
-- =========================================================
-- MIDDLE-OFFICE AI AGENT AUTOMATED REPAIR SCRIPT
-- GENERATED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- TARGET: TRADE_ID {trade_id} | ERROR: {error_type}
-- =========================================================
UPDATE trade_ledger 
SET broker_lei = '{correct_lei}', 
    operational_status = 'STP_READY', 
    last_modified_by = 'AI_OPERATIONAL_AGENT'
WHERE trade_id = '{trade_id}';
"""
            return sql_script
            
        elif error_type == "INVALID_CURRENCY":
            correct_ccy = analysis.get("fix_suggestion")
            sql_script = f"""
-- =========================================================
-- MIDDLE-OFFICE AI AGENT AUTOMATED REPAIR SCRIPT
-- GENERATED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- TARGET: TRADE_ID {trade_id} | ERROR: {error_type}
-- =========================================================
UPDATE trade_ledger 
SET currency = '{correct_ccy}', 
    operational_status = 'STP_READY', 
    last_modified_by = 'AI_OPERATIONAL_AGENT'
WHERE trade_id = '{trade_id}';
"""
            return sql_script
            
        return "-- No repair needed. Trade is Straight-Through Processing (STP) compliant."

if __name__ == "__main__":
    # Simulated broken institutional trade payload sent by a counterparty broker
    broken_broker_payload = {
        "trade_id": "TRD-2026-9901",
        "asset_class": "Equity",
        "security": "AAPL",
        "quantity": 5000,
        "price": 175.00,
        "counterparty": "GOLDMAN_SACHS",
        "broker_lei": "INCORRECT_LEI_99999999",
        "currency": "USD"
    }
    
    # Initialize the operational agent
    agent = TradeExceptionAgent()
    
    print("Executing ingestion triage pipeline...")
    analysis = agent.triage_exception(json.dumps(broken_broker_payload))
    
    print(f"Exception Found! Type: {analysis['error_type']} on Field: '{analysis['field']}'")
    print("Querying MCP reference tools to generate database repair data...")
    
    sql_patch = agent.generate_sql_repair(analysis)
    print(sql_patch)
