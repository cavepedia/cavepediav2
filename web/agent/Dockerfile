# syntax=docker/dockerfile:1

FROM langchain/langgraph-api:3.12

# Copy dependency files and install
ADD pyproject.toml uv.lock /deps/agent/
RUN cd /deps/agent && pip install --no-cache-dir -e .

# Copy application code
ADD main.py langgraph.json /deps/agent/

# Set the graph configuration
ENV LANGSERVE_GRAPHS='{"vpi_1000": "/deps/agent/main.py:graph"}'
