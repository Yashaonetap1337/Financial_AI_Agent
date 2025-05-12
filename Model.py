import os
from dotenv import load_dotenv
from smolagents import OpenAIServerModel
load_dotenv()

model = OpenAIServerModel(
    model_id="deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
    api_base="https://api.together.xyz/v1/",
    api_key=os.environ["TOGETHER_API_KEY"],
    temperature=0.0,
)