import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";

import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";
import { auth0 } from "@/lib/auth0";

const serviceAdapter = new ExperimentalEmptyAdapter();

export const POST = async (req: NextRequest) => {
  // Get user session and roles
  const session = await auth0.getSession();
  const userRoles = (session?.user?.roles as string[]) || [];

  // Get sources-only mode from query param
  const url = new URL(req.url);
  const sourcesOnly = url.searchParams.get("sourcesOnly") === "true";

  console.log("DEBUG: User roles from session:", userRoles);
  console.log("DEBUG: Sources only mode:", sourcesOnly);

  // Create HttpAgent with user roles and sources-only headers
  const agent = new HttpAgent({
    url: process.env.AGENT_URL || "http://localhost:8000/",
    headers: {
      "x-user-roles": JSON.stringify(userRoles),
      "x-sources-only": sourcesOnly ? "true" : "false",
    },
  });

  const runtime = new CopilotRuntime({
    agents: {
      vpi_1000: agent,
    },
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
