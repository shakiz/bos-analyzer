import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";  // your App component

const root = createRoot(document.getElementById("root"));
root.render(<App />);