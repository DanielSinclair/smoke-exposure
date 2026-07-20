import dashboardData from "../public/data/dashboard.json";
import Dashboard, { type DashboardData } from "./Dashboard";

export default function Home() {
  return <Dashboard initialData={dashboardData as DashboardData} />;
}
