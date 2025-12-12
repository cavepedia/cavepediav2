import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";

import { NextRequest } from "next/server";
import { auth0 } from "@/lib/auth0";

// 1. You can use any service adapter here for multi-agent support. We use
//    the empty adapter since we're only using one agent.
const serviceAdapter = new ExperimentalEmptyAdapter();

// 3. Build a Next.js API route that handles the CopilotKit runtime requests.
export const POST = async (req: NextRequest) => {
  // Get Auth0 session
  const session = await auth0.getSession();

  // Extract roles from session
  const userRoles = session?.user?.roles || [];

  console.log("[copilotkit] session exists:", !!session);
  console.log("[copilotkit] userRoles:", userRoles);

  // 2. Create the CopilotRuntime instance with remote endpoint
  const runtime = new CopilotRuntime({
    remoteEndpoints: [
      {
        url: `${process.env.LANGGRAPH_DEPLOYMENT_URL || "http://localhost:8000"}/copilotkit`,
      },
    ],
    // Pass auth context as properties to the remote endpoint
    properties: {
      auth0_user_roles: userRoles,
    },
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};