import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
MAX_STEPS = 6

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def list_files(folder: str) -> str:
    """Lists the files and folders inside a folder.

    Args:
        folder: Path of the folder, for example "."
    """
    try:
        names = sorted(os.listdir(folder))
    except OSError as error:
        return f"Error: {error}"
    return "\n".join(names) if names else "(empty folder)"


TOOLS = {"list_files": list_files}


def run_agent(task: str) -> str:
    config = types.GenerateContentConfig(
        tools=[list_files],
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
            print(f"Step {step}: tool {call.name} {dict(call.args)}")
            result = TOOLS[call.name](**call.args)
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
    print(run_agent("What files are in the current folder? Summarize in one sentence."))