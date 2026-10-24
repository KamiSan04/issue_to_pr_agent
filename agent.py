import time
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors
from tools import TOOL_FUNCTIONS, TOOLS

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
MAX_STEPS = 10
MAX_RETRIES = 4
STEP_PAUSE = 13
RETRY_WAIT = 40

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def run_tool(name: str, args: dict) -> str:
    if name not in TOOLS:
        return f"Error: unknown tool {name}"
    try:
        return TOOLS[name](**args)
    except TypeError as error:
        return f"Error: bad arguments: {error}"

def call_model(contents, config):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return client.models.generate_content(
                model=MODEL, contents=contents, config=config
            )
        except errors.ClientError as error:
            if error.code != 429 or attempt == MAX_RETRIES:
                raise
            if "PerDay" in str(error):
                raise
            print(f"Rate limit hit. Waiting {RETRY_WAIT} seconds...")
            time.sleep(RETRY_WAIT)

def run_agent(task: str) -> str:
    config = types.GenerateContentConfig(
        tools=TOOL_FUNCTIONS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=task)])]

    for step in range(1, MAX_STEPS + 1):
        response = call_model(contents, config)
        calls = response.function_calls
        if not calls:
            return response.text

        contents.append(response.candidates[0].content)
        result_parts = []
        for call in calls:
            args = dict(call.args)
            print(f"Step {step}: tool {call.name} {args}")
            result = run_tool(call.name, args)
            result_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        id=call.id,
                        name=call.name,
                        response={"result": result},
                    )
                )
            )
        contents.append(types.Content(role="user", parts=result_parts))
        time.sleep(STEP_PAUSE)

    return "Stopped: too many steps."


if __name__ == "__main__":
    print(
        run_agent(
            "Run the tests. If any fail, read the code, fix the bug, "
            "and run the tests again. Then tell me what you changed."
        )
    )