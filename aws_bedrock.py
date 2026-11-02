import boto3
import logging
import os
import json

from pydantic import BaseModel, Field
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)
# Configure logging to show INFO and above, with a helpful format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


KB_ID = os.environ.get("KB_ID", "")
DS_ID = os.environ.get("DS_ID", "")
MODEL_NAME = os.environ.get("BEDROCK_MODEL_NAME", "")
AWS_REGION = os.environ.get("AWS_REGION", "")

class RecipeResponse(BaseModel):
    found: bool = Field(
        description="Whether the requested recipe exists in the context"
    )
    recipe_name: str = Field(
        description="Name of the requested recipe"
    )
    cuisine: str | None = Field(
        description="Cuisine or country, if explicitly provided"
    )
    preparation_time: str | None = Field(
        description="Preparation time, if explicitly provided"
    )
    refrigeration_time: str | None = Field(
        description="Refrigeration time, if explicitly provided"
    )
    ingredients: list[str] = Field(
        description="Ingredients and quantities found in the context"
    )
    instructions: list[str] = Field(
        description="Cooking instructions in the correct order"
    )

COOKBOOK_SYSTEM_PROMPT = """
You are a cookbook recipe formatter.

Your task is to extract the requested recipe from the supplied context
and present only the final answer.

STRICT RULES:
1. Never output your analysis, reasoning, or search process.
2. Never write phrases such as "Let me analyze", "Looking at the context",
   "I found", "Let me check", or "The user is asking".
3. Do not describe how you selected the recipe.
4. Do not repeat the recipe or conclusion.
5. Do not include unrelated recipes.
6. Do not invent ingredients, quantities, or instructions.
7. Ignore PDF extraction artifacts and control characters.
8. Extract ingredients and quantities from the instructions if a
   separate ingredient list is unavailable.
9. If a quantity is ambiguous or contradictory, preserve the source
   wording or explicitly mark it as unclear. Do not guess.
10. Return only readable Markdown using this format. If information is unavailable, omit that field.
11. If the requested recipe cannot be found in the context, respond: "I couldn't find this recipe in the provided cookbook context."

OUTPUT ONLY THE FINAL RECIPE. NO PREFACE. NO ANALYSIS.
""".strip()


class AWSBedRock:

    def __init__(self):
        session = boto3.Session()
        self.bedrock_client = session.client(service_name="bedrock-agent", region_name=AWS_REGION)
        self.bedrock_agent = session.client(service_name="bedrock-agent-runtime", region_name=AWS_REGION)
        self.bedrock_runtime = session.client(service_name="bedrock-runtime", region_name=AWS_REGION)

    def start_ingestion(self):
        try:
            res = self.bedrock_client.start_ingestion_job(
                knowledgeBaseId=KB_ID,
                dataSourceId=DS_ID
            )
            return res
        except ClientError as err:
            logger.error(f"Error occured during KB ingestion. {err.response}")

    def retrieve_ingestion(self, query, top_k):
        try:
            retrieved_content = self.bedrock_agent.retrieve(
                knowledgeBaseId=KB_ID,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "managedSearchConfiguration": {
                        "numberOfResults": top_k
                    }
                }
            )
            results = retrieved_content.get("retrievalResults", [])
            context = "\n\n".join(
                item.get("content", {}).get("text", "")
                for item in results
                if item.get("content", {}).get("text")
            )
            return self.bedrock_converse(context, query, results)
        except ClientError as err:
            logger.error(f"Error occurred while retrieving the content from bedrock. {err.response}")

    def bedrock_converse(self, context, query, results):

        try:
            schema = RecipeResponse.model_json_schema()
            prompt = f"""
            Extract the requested recipe from the context.
            Return only a JSON object matching this schema. Do not include Markdown fences.
            Use null for unknown text values and [] for unknown lists.
            
            Schema:
            {json.dumps(schema)}
            
            Context:
            {context}
            
            Question:
            {query}
            """
            generated = self.bedrock_runtime.converse(
                modelId=MODEL_NAME,
                system=[{"text": COOKBOOK_SYSTEM_PROMPT}],
                messages=[{
                    "role": "user",
                    "content": [{"text": prompt}]
                }],
                inferenceConfig={
                    "maxTokens": 700,
                    "temperature": 0.1,
                }
            )
            answer = generated["output"]["message"]["content"][0]["text"]

            return answer
        except ClientError as err:
            logger.error(f"Error while calling bedrock llm. {err.response}")