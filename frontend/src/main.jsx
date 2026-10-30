
import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App.jsx";
import BidholiMap from "./BidholiMap.jsx";

import "./index.css";

const isBidholiMap =
  window.location.pathname === "/bidholi";

ReactDOM.createRoot(
  document.getElementById("root")
).render(
  <React.StrictMode>
    {isBidholiMap ? <BidholiMap /> : <App />}
  </React.StrictMode>
);
