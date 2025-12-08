import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";

import { LangGraphAgent } from "@ag-ui/langgraph"
import { NextRequest } from "next/server";
import { auth0 } from "@/lib/auth0";

// 1. You can use any service adapter here for multi-agent support. We use
//    the empty adapter since we're only using one agent.
const serviceAdapter = new ExperimentalEmptyAdapter();

// 3. Build a Next.js API route that handles the CopilotKit runtime requests.
export const POST = async (req: NextRequest) => {
  // Get Auth0 session
  const session = await auth0.getSession();

  // Extract access token and roles from session
  const accessToken = session?.accessToken;
  const userRoles = session?.user?.roles || [];

  // 2. Create the CopilotRuntime instance with Auth0 configuration
  const runtime = new CopilotRuntime({
    agents: {
      "sample_agent": new LangGraphAgent({
        deploymentUrl: process.env.LANGGRAPH_DEPLOYMENT_URL || "http://localhost:8123",
        graphId: "sample_agent",
        langsmithApiKey: process.env.LANGSMITH_API_KEY || "",
        langgraphConfig: {
          configurable: {
            auth0_access_token: accessToken,
            auth0_user_roles: userRoles,
          }
        }
      }),
    }
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};