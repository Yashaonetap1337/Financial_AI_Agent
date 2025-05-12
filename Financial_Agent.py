from smolagents import ToolCallingAgent
from Tools import ListTablesTool, ExecuteQueryTool, CurrencyConversionTool, CalculatorTool
from prompts import Financial_Agent_Prompt
from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv
from smolagents import ToolCallingAgent
from sqlalchemy import create_engine, inspect
from Model import model
load_dotenv()


engine = create_engine("sqlite:///user_transactions.db") 
inspector = inspect(engine)
currency_api_key = os.environ["currency_api_key"]

list_tables_tool = ListTablesTool()
execute_query_tool = ExecuteQueryTool(engine)
calculator_tool = CalculatorTool()
currency_tool = CurrencyConversionTool(currency_api_key)

Financial_Agent = ToolCallingAgent(
    tools = [ list_tables_tool, execute_query_tool, calculator_tool, currency_tool],
    model = model,
)
Financial_Agent.prompt_templates['system_prompt'] = Financial_Agent_Prompt
print(Financial_Agent.prompt_templates['system_prompt'])