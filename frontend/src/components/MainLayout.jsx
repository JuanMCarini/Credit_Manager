import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useEffect } from 'react';
import useAppStore from '../store/useAppStore';

const MainLayout = () => {
  const { fetchAuxiliares, checkApiStatus } = useAppStore();

  useEffect(() => {
    checkApiStatus();
    fetchAuxiliares();
  }, [checkApiStatus, fetchAuxiliares]);

  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
};

export default MainLayout;
