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

  console.log("DEBUG: User roles from session:", userRoles);

  // Create HttpAgent with user roles header
  const agent = new HttpAgent({
    url: process.env.AGENT_URL || "http://localhost:8000/",
    headers: {
      "x-user-roles": JSON.stringify(userRoles),
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
