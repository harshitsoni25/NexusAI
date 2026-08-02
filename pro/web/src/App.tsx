import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import NewJob from "./pages/NewJob";
import JobHistory from "./pages/JobHistory";
import JobProgress from "./pages/JobProgress";
import DatasetExplorer from "./pages/DatasetExplorer";
import ExportCenter from "./pages/ExportCenter";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";
import Logs from "./pages/Logs";
import PluginManager from "./pages/PluginManager";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/new" element={<NewJob />} />
        <Route path="/jobs" element={<JobHistory />} />
        <Route path="/progress" element={<JobProgress />} />
        <Route path="/datasets" element={<DatasetExplorer />} />
        <Route path="/exports" element={<ExportCenter />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/plugins" element={<PluginManager />} />
        <Route path="/logs" element={<Logs />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  );
}
