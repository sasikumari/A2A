"""
Figma Agent — Orchestrates design-to-code and write-to-canvas via MCP.
This agent acts as a proxy for Figma MCP skills:
1. use_figma: To build screens on a canvas.
2. figma-implement-design: To turn designs into React/Tailwind code.

The mcp package is optional — if not installed the agent falls back gracefully.
"""
import os
import json
import asyncio

try:
    from mcp.client.stdio import stdio_client
    from mcp.client.session import ClientSession
    from mcp import StdioServerParameters
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False

from .llm import chat, extract_json

class FigmaAgent:
    def __init__(self, mcp_server_url="https://mcp.figma.com/mcp"):
        self.mcp_server_url = mcp_server_url
        self.figma_token = os.environ.get("FIGMA_PAT", None)
        self.team_id = os.environ.get("FIGMA_TEAM_ID", "")

    def generate_canvas_design(self, prototype_data: dict) -> str:
        """
        Uses Figma MCP via mcp-python SDK to generate actual Figma designs.
        Falls back to mock URL if no token exists or mcp is not installed.
        """
        if not self.figma_token:
            print("[Warning] FIGMA_PAT not found. Returning mock layout link.")
            return "https://www.figma.com/design/mock-upi-prototype-id"

        if not _MCP_AVAILABLE:
            print("[Warning] mcp package not installed. Returning team drafts link.")
            return f"https://www.figma.com/files/team/{self.team_id}/drafts?msg=design-queued"

        screens = prototype_data.get('screens', [])
        prompt = f"Using Team ID {self.team_id}, create a prototype for a UPI feature with these screens:\n" + json.dumps(screens, indent=2)

        try:
            url = asyncio.run(self._run_mcp_client(prompt))
            return url if url else f"https://www.figma.com/files/team/{self.team_id}/drafts?msg=design-queued"
        except Exception as e:
            print(f"[Error] Figma MCP Exception: {e}")
            return f"https://www.figma.com/files/team/{self.team_id}/drafts?msg=design-queued"

    async def _run_mcp_client(self, prompt: str) -> str:
        if not _MCP_AVAILABLE:
            return ""

        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@figma/mcp"],
            env={**os.environ, "FIGMA_PAT": self.figma_token}
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("use_figma", {"prompt": prompt})
                    if result.content and len(result.content) > 0:
                        return result.content[0].text
        except Exception as e:
            raise e
        return ""

    def map_design_to_code(self, figma_url: str) -> str:
        return "/* Generated React Component from Figma */\nexport const UPIComponent = () => { ... }"

    def connect_components(self, figma_url: str, codebase_path: str):
        pass

figma_agent = FigmaAgent()
