import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import AgentPage from './pages/agent';
import DashboardPage from './pages/dashboard';
import GovernancePage from './pages/governance';
import KeysPage from './pages/keys';
import KnowledgePage from './pages/knowledge';
import LoginPage from './pages/login';
import ModelsPage from './pages/models';
import ObservePage from './pages/observe';
import ProfilePage from './pages/profile';
import ProvidersPage from './pages/providers';
import ProviderDetailPage from './pages/providers/detail';
import ProviderCreatePage from './pages/providers/new';
import RepoPage from './pages/repo';
import SettingsPage from './pages/settings';
import SkillDetailPage from './pages/skills/detail';
import SkillsListPage from './pages/skills';

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('tap_token');
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <MainLayout>
                <DashboardPage />
              </MainLayout>
            </RequireAuth>
          }
        />
        {[
          ['/repos', <RepoPage />],
          ['/agents', <AgentPage />],
          ['/skills', <SkillsListPage />],
          ['/skills/:skillId', <SkillDetailPage />],
          ['/knowledge', <KnowledgePage />],
          ['/observe', <ObservePage />],
          ['/settings', <SettingsPage />],
          ['/profile', <ProfilePage />],
          ['/keys', <KeysPage />],
          ['/models', <ModelsPage />],
          ['/providers', <ProvidersPage />],
          ['/providers/new', <ProviderCreatePage />],
          ['/providers/:providerId', <ProviderDetailPage />],
          ['/governance', <GovernancePage />],
        ].map(([path, element]) => (
          <Route
            key={path as string}
            path={path as string}
            element={
              <RequireAuth>
                <MainLayout>{element as React.ReactNode}</MainLayout>
              </RequireAuth>
            }
          />
        ))}
        {['/teams', '/projects', '/tasks', '/plugins'].map((path) => (
          <Route
            key={path}
            path={path}
            element={<Navigate to="/governance" replace />}
          />
        ))}
        <Route path="/users" element={<Navigate to="/settings" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
