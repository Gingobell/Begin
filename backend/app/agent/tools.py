"""
Tool registry — re-exports tools defined in graph.py.

Tools are defined in graph.py so they can access RunnableConfig
for user_id injection. This module provides a clean import surface
for any code that needs the tool list without importing the full graph.
"""
from app.agent.graph import search_diaries

ALL_TOOLS = [search_diaries]
