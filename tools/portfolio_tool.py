# /wealth-advisor/tools/portfolio_tool.py

from google.generativeai.experimental import adk
from google.cloud import bigquery
import os
import json
import logging
import pandas as pd

# Initialize clients once to be reused
try:
    bq_client = bigquery.Client()
except Exception as e:
    logging.error(f"Failed to initialize BigQuery client: {e}")
    bq_client = None

DATASET_ID = os.environ.get("DATASET_ID")

@adk.tool
def get_user_portfolio_summary(client_id: str) -> str:
    """
    Fetches the total market value and top 3 holdings for a given client_id.
    Returns a JSON string with total_market_value and a list of top_holdings.
    """
    if not bq_client or not DATASET_ID:
        return json.dumps({"error": "BigQuery client or DATASET_ID is not configured."})

    query = f"""
    WITH PortfolioSummary AS (
        SELECT
            client_id,
            SUM(market_value) as total_market_value,
            ARRAY_AGG(
                STRUCT(ticker, security_name, market_value)
                ORDER BY market_value DESC
                LIMIT 3
            ) AS top_holdings
        FROM `{DATASET_ID}.holdings`
        WHERE client_id = @client_id
        GROUP BY client_id
    )
    SELECT
        total_market_value,
        (SELECT ARRAY_AGG(th) FROM UNNEST(top_holdings) AS th) AS top_holdings
    FROM PortfolioSummary
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("client_id", "STRING", client_id)]
    )
    try:
        logging.info(f"Executing portfolio query for client_id: {client_id}")
        results_df = bq_client.query(query, job_config=job_config).to_dataframe()
        
        if results_df.empty:
            logging.warning(f"No portfolio data found for client_id: {client_id}")
            return json.dumps({"error": "No portfolio data found for this user."})
        
        # Convert NumPy types to native Python types for JSON serialization
        results_df['top_holdings'] = results_df['top_holdings'].apply(
            lambda x: [dict(row) for row in x] if isinstance(x, list) else []
        )
        if 'total_market_value' in results_df.columns:
            results_df['total_market_value'] = results_df['total_market_value'].astype(float)

        return results_df.to_json(orient='records')

    except Exception as e:
        logging.error(f"BigQuery query failed for client_id {client_id}: {e}")
        return json.dumps({"error": "An error occurred while fetching portfolio data."})