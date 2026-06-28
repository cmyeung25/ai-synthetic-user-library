import React from "react";
import { createRoot } from "react-dom/client";

import { Stage15WorkspaceShellHost } from "./Stage15WorkspaceShellHost.jsx";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Framework host root element is missing.");
}

createRoot(rootElement).render(<Stage15WorkspaceShellHost />);
