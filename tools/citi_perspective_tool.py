# /wealth-advisor/tools/citi_perspective_tool.py

from google.generativeai.tools import tool
from google.cloud import discoveryengine_v1 as discoveryengine
import os
import json
import logging

# Initialize clients once
try:
    search_client = discoveryengine.SearchServiceClient()
except Exception as e:
    logging.error(f"Failed to initialize Discovery Engine client: {e}")
    search_client = None

PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
LOCATION = os.environ.get("DATA_STORE_LOCATION", "global")
DATA_STORE_ID = os.environ.get("DATA_STORE_ID")

@tool
def get_citi_perspective(query: str) -> str:
    """
    Searches Citi's internal knowledge base for official perspectives,
    recommendations, policies, or answers to FAQs. Use this tool to answer
    questions about Citi's market outlook or internal procedures.
    """
    if not PROJECT_ID:
        raise ValueError("GCP_PROJECT_ID environment variable not set.")
    if not DATA_STORE_ID:
        raise ValueError("DATA_STORE_ID environment variable not set.")

    if not search_client:
        return json.dumps({"error": "Vertex AI Search client is not configured."})

    serving_config = search_client.serving_config_path(
        project=PROJECT_ID,
        location=LOCATION,
        data_store=DATA_STORE_ID,
        serving_config="default_config",
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=3,
        content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
            summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                summary_result_count=3,
                include_citations=True,
            ),
            extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                max_extractive_answer_count=3
            )
        )
    )

    try:
        logging.info(f"Querying Vertex AI Search with query: '{query}'")
        response = search_client.search(request)
        
        # Use the high-level summary if available
        if response.summary and response.summary.summary_text:
            return json.dumps({"summary": response.summary.summary_text})
            
        # Otherwise, build results from individual documents
        results = [
            {
                "title": result.document.derived_struct_data.get("title", "N/A"),
                "link": result.document.derived_struct_data.get("link", "N/A"),
                "snippet": snippet.get("snippet", "N/A")
            }
            for result in response.results
            for snippet in result.document.derived_struct_data.get("snippets", [])
        ]

        if not results:
            logging.warning(f"No internal guidance found for query: '{query}'")
            return json.dumps({"error": "No internal guidance found for this query."})

        return json.dumps(results)
    except Exception as e:
        logging.error(f"An error occurred while querying internal knowledge: {e}")
        return json.dumps({"error": f"An error occurred while querying internal knowledge: {str(e)}"})