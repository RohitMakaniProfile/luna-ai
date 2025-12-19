import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css"; // ✅ Changed from '@' to './' (Safer)
import App from "./App"; // ✅ Changed from '@' to './'
import { Toaster } from "./components/ui/toaster"; // ✅ Toaster activate kiya

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
    <Toaster /> {/* Ab notifications screen par dikhenge */}
  </React.StrictMode>
);