"use client";

import { useCopilotAction } from "@copilotkit/react-core";
import { CopilotKitCSSProperties, CopilotChat } from "@copilotkit/react-ui";
import { useState } from "react";

export default function CopilotKitPage() {
  const [themeColor, setThemeColor] = useState("#6366f1");

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

  return (
    <main
      style={{ "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties}
      className="h-screen w-screen flex justify-center bg-gray-50 py-8 px-2"
    >
      <div className="h-full w-full max-w-5xl flex flex-col">
        <CopilotChat
          instructions={"You assist with looking up any relevant information to caving. This includes but is not limited to Cave Locations, Cave Surveying, Cave History."}
          labels={{
            title: "AI Cartwright",
            initial: "Would you like to lookup a cave location today?",
          }}
          className="h-full w-full"
        />
      </div>
    </main>
  );
}
