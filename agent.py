import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tools import TOOL_FUNCTIONS, TOOLS

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
MAX_STEPS = 10

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def run_tool(name: str, args: dict) -> str:
    if name not in TOOLS:
        return f"Error: unknown tool {name}"
    try:
        return TOOLS[name](**args)
    except TypeError as error:
        return f"Error: bad arguments: {error}"


def run_agent(task: str) -> str:
    config = types.GenerateContentConfig(
        tools=TOOL_FUNCTIONS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=task)])]

    for step in range(1, MAX_STEPS + 1):
        response = client.models.generate_content(
            model=MODEL, contents=contents, config=config
        )
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

    return "Stopped: too many steps."


if __name__ == "__main__":
    print(
        run_agent(
            "Create hello.txt containing 'hello robot'. "
            "Then run git status and tell me what you see."
        )
    )