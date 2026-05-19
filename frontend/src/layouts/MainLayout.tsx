import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { clearToken } from '../lib/api';

const NAV_ITEMS: Array<{ path: string; label: string } | null> = [
  { path: '/', label: '控制台' },
  { path: '/governance', label: '治理中心' },
  { path: '/observe', label: '观测中心' },
  null,
  { path: '/providers', label: 'AI 服务商' },
  { path: '/models', label: '模型注册' },
  { path: '/keys', label: '虚拟密钥' },
  { path: '/skills', label: '技能平台' },
  { path: '/agents', label: '智能体' },
  { path: '/knowledge', label: '知识库(RAG)' },
  { path: '/repos', label: '代码仓库' },
  null,
  { path: '/users', label: '用户管理' },
  { path: '/settings', label: '设置' },
  { path: '/profile', label: '个人中心' },
];

const MainLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    clearToken();
    navigate('/login');
  };

  const isActivePath = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'system-ui, sans-serif' }}>
      {/* Sidebar */}
      <aside style={{ width: 200, background: '#001529', color: '#fff', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '20px 16px', fontSize: 16, fontWeight: 700, borderBottom: '1px solid #122840' }}>
          Team AI Platform
          <div style={{ marginTop: 8, fontSize: 11, color: '#8fb5d8', fontWeight: 500 }}>
            Governance Core Mode
          </div>
        </div>
        <nav style={{ flex: 1, paddingTop: 8, overflowY: 'auto' }}>
          {NAV_ITEMS.map((item, i) =>
            item === null ? (
              <div key={`divider-${i}`} style={{ margin: '8px 16px 4px', fontSize: 10, color: '#456', textTransform: 'uppercase', letterSpacing: 1, borderTop: '1px solid #122840', paddingTop: 10 }}>AI 治理核心</div>
            ) : (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  display: 'block',
                  padding: '9px 20px',
                  color: isActivePath(item.path) ? '#1677ff' : '#ccc',
                  background: isActivePath(item.path) ? '#0d2136' : 'transparent',
                  textDecoration: 'none',
                  fontSize: 13,
                }}
              >
                {item.label}
              </Link>
            )
          )}
        </nav>
        <button
          onClick={handleLogout}
          style={{ margin: 12, padding: '8px 0', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
        >
          退出登录
        </button>
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, background: '#f5f7fa', minHeight: '100vh' }}>
        <div style={{ padding: 24 }}>{children}</div>
      </main>
    </div>
  );
};

export default MainLayout;
