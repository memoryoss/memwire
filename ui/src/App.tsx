import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Playground from "@/pages/Playground";
import Memory from "@/pages/Memory";
import Knowledge from "@/pages/Knowledge";
import Sessions from "@/pages/Sessions";
import APIKeys from "@/pages/APIKeys";
import Settings from "@/pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="playground" element={<Playground />} />
        <Route path="memory" element={<Memory />} />
        <Route path="knowledge" element={<Knowledge />} />
        <Route path="sessions" element={<Sessions />} />
        <Route path="api-keys" element={<APIKeys />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
