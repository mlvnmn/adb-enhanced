import Sidebar from './components/Sidebar';
import TopNav from './components/TopNav';
import StatCards from './components/StatCards';
import BehaviorChart from './components/BehaviorChart';
import AnomalyPanel from './components/AnomalyPanel';
import ActivityLog from './components/ActivityLog';
import ActionButtons from './components/ActionButtons';
import { useSocket } from './hooks/useSocket';

export default function App() {
  const { connected, hasDevice, logs, anomalies, foreground, socket } = useSocket();

  return (
    <>
      <div className="app-container">
        <Sidebar socket={socket} />
        <main className="main-content">
          <TopNav connected={connected} hasDevice={hasDevice} socket={socket} />
          <StatCards logs={logs} connected={connected} hasDevice={hasDevice} socket={socket} />

          <div className="dashboard-row-top">
            <div className="chart-col">
              <BehaviorChart logs={logs} />
            </div>
            <div className="anomaly-col">
              <AnomalyPanel anomalies={anomalies} />
            </div>
          </div>

          <div className="dashboard-row-bottom">
            <ActivityLog logs={logs} hasDevice={hasDevice} />
          </div>

          <ActionButtons />
        </main>
      </div>
      <div className="bg-glow-1"></div>
      <div className="bg-glow-2"></div>
    </>
  );
}
