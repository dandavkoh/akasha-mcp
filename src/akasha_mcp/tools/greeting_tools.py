def register(mcp):
    @mcp.tool()
    def greet(name: str) -> str:
        """Greet a person"""
        return f"Hello {name}!"