import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";

// PWA Service Worker 등록
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(console.error);

    // 네트워크 복구 시 Background Sync 트리거
    window.addEventListener("online", async () => {
      const reg = await navigator.serviceWorker.ready;
      if ("sync" in reg) {
        await (reg as ServiceWorkerRegistration & { sync: { register(tag: string): Promise<void> } })
          .sync.register("sync-recordings");
      }
    });
  });
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
