"use client";

import { useCopilotAction, useCopilotChat } from "@copilotkit/react-core";
import { CopilotKitCSSProperties, CopilotChat } from "@copilotkit/react-ui";
import { useState } from "react";
import { useUser } from "@auth0/nextjs-auth0/client";
import LoginButton from "@/components/LoginButton";
import LogoutButton from "@/components/LogoutButton";

// Separate component to safely use useCopilotChat hook
function ThinkingIndicator() {
  try {
    const { isLoading } = useCopilotChat();
    if (!isLoading) return null;
    return (
      <div className="absolute bottom-24 left-1/2 transform -translate-x-1/2 bg-white shadow-lg rounded-full px-4 py-2 flex items-center gap-2 z-50">
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
          <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
          <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
        </div>
        <span className="text-sm text-gray-600">Thinking...</span>
      </div>
    );
  } catch {
    return null;
  }
}

export default function CopilotKitPage() {
  const [themeColor, setThemeColor] = useState("#6366f1");
  const { user, isLoading: authLoading } = useUser();

  useCopilotAction({
    name: "setThemeColor",
    parameters: [{
      name: "themeColor",
      description: "The theme color to set. Make sure to pick nice colors.",
      required: true,
    }],
    handler({ themeColor }) {
      setThemeColor(themeColor);
    },
  });

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="app-container">
        <div className="loading-state">
          <div className="loading-text">Loading...</div>
        </div>
      </div>
    );
  }

  // If not authenticated, show login page
  if (!user) {
    return (
      <div className="app-container">
        <div className="main-card-wrapper">
          <img
            src="https://cdn.auth0.com/quantum-assets/dist/latest/logos/auth0/auth0-lockup-en-ondark.png"
            alt="Auth0 Logo"
            className="auth0-logo"
          />
          <h1 className="main-title">Cavepedia</h1>

          <div className="action-card">
            <p className="action-text">
              Welcome! Please log in to access the AI Cave Chat.
            </p>
            <LoginButton />
          </div>
        </div>
      </div>
    );
  }

  // If authenticated, show the CopilotKit chat with user profile
  return (
    <main
      style={{ "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties}
      className="h-screen w-screen flex flex-col bg-gray-50"
    >
      {/* Header with user profile and logout */}
      <div className="w-full bg-white shadow-sm border-b border-gray-200 px-4 py-3">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold text-gray-900">Cavepedia</h1>
          </div>
          <div className="flex items-center gap-4">
            {user.picture && (
              <img
                src={user.picture}
                alt={user.name || 'User'}
                className="w-8 h-8 rounded-full"
              />
            )}
            <div className="flex flex-col items-end">
              <span className="text-sm text-gray-700">{user.name}</span>
              {(user as any).roles && (user as any).roles.length > 0 && (
                <span className="text-xs text-gray-500">
                  {(user as any).roles.join(', ')}
                </span>
              )}
            </div>
            <LogoutButton />
          </div>
        </div>
      </div>

      {/* CopilotKit Chat */}
      <div className="flex-1 flex justify-center py-8 px-2 overflow-hidden relative">
        <div className="h-full w-full max-w-5xl flex flex-col">
          <CopilotChat
            instructions={"You are a knowledgeable caving assistant. Help users with all aspects of caving including cave exploration, safety, surveying techniques, cave locations, geology, equipment, history, conservation, and any other caving-related topics. Provide accurate, helpful, and safety-conscious information. CRITICAL: Always cite sources at the end of each response."}
            labels={{
              title: "AI Cartwright",
              initial: "Hello! I'm here to help with anything related to caving. Ask me about caves, techniques, safety, equipment, or anything else caving-related!",
            }}
            className="h-full w-full"
          />
        </div>
        <ThinkingIndicator />
      </div>
    </main>
  );
}
