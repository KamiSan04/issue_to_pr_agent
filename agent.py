import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_STEPS = 10
MAX_RETRIES = 5
STEP_PAUSE = 13
RETRY_WAIT = 40
TOOL_TIMEOUT = 150

TASK = (
    "Run the tests. If any fail, read the code, fix the bug, "
    "and run the tests again. Then tell me what you changed."
)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

SERVER = StdioServerParameters(
    command=sys.executable,
    args=["mcp_server.py"],
    cwd=str(Path(__file__).parent),
)


async def call_model(contents, config):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await client.aio.models.generate_content(
                model=MODEL, contents=contents, config=config
            )
        except (errors.ClientError, errors.ServerError) as error:
            retryable = error.code in (429, 503)
            if not retryable or attempt == MAX_RETRIES or "PerDay" in str(error):
                raise
            wait = RETRY_WAIT if error.code == 429 else 10 * attempt
            print(f"Error {error.code}. Waiting {wait} seconds...")
            await asyncio.sleep(wait)


async def run_tool(session, name, args):
    try:
        result = await asyncio.wait_for(
            session.call_tool(name, args), timeout=TOOL_TIMEOUT
        )
    except asyncio.TimeoutError:
        return f"Error: tool {name} timed out after {TOOL_TIMEOUT} seconds."
    except Exception as error:
        return f"Error: {error}"
    text = "\n".join(block.text for block in result.content if hasattr(block, "text"))
    return text or "(no output)"


async def agent_loop(session, task, config):
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=task)])]

    for step in range(1, MAX_STEPS + 1):
        response = await call_model(contents, config)
        calls = response.function_calls
        if not calls:
            return response.text

        contents.append(response.candidates[0].content)
        result_parts = []
        for call in calls:
            args = dict(call.args)
            print(f"Step {step}: tool {call.name} {args}")
            result = await run_tool(session, call.name, args)
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
        await asyncio.sleep(STEP_PAUSE)

    return "Stopped: too many steps."


async def run_agent(task: str) -> str:
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listing = await session.list_tools()
            declarations = [
                types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description or "",
                    parameters_json_schema=tool.inputSchema,
                )
                for tool in listing.tools
            ]
            config = types.GenerateContentConfig(
                tools=[types.Tool(function_declarations=declarations)],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            )
            return await agent_loop(session, task, config)


if __name__ == "__main__":
    print(asyncio.run(run_agent(TASK)))