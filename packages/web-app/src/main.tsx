/**
 * React application entry point.
 * Mounts the App component into the #root DOM element.
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/globals.css";
import { App } from "./App";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error(
    "[kinemind] Fatal: <div id='root'> not found in index.html. " +
      "Check that index.html contains <div id='root'></div>.",
  );
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
