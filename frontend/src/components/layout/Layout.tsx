import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/auth';
import styles from './Layout.module.css';

const NAV = [
  { to: '/dashboard', icon: '⚡', label: 'Dashboard'   },
  { to: '/inbox',     icon: '💬', label: 'Bandeja IA'  },
  { to: '/inventory', icon: '📦', label: 'Inventario'  },
  { to: '/analytics', icon: '📊', label: 'Analytics'   },
  { to: '/sales',     icon: '💰', label: 'Ventas'      },
];

export default function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className={styles.root}>
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className={styles.sidebar}>
        {/* Logo */}
        <div className={styles.logo}>
          <div className={styles.logoIcon}>⚡</div>
          <div>
            <div className={styles.logoName}>Stock360</div>
            <div className={styles.logoTag}>AI SALES AGENT</div>
          </div>
        </div>

        {/* Aria status */}
        <div className={styles.ariaStatus}>
          <span className={styles.dot} />
          Aria activa · IA en línea
        </div>

        {/* Nav */}
        <nav className={styles.nav}>
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `${styles.navItem} ${isActive ? styles.navActive : ''}`
              }
            >
              <span className={styles.navIcon}>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div className={styles.userBlock}>
          <div className={styles.userAvatar}>
            {user?.full_name?.charAt(0).toUpperCase() ?? 'U'}
          </div>
          <div className={styles.userInfo}>
            <div className={styles.userName}>{user?.full_name}</div>
            <div className={styles.userRole}>{user?.role}</div>
          </div>
          <button className={styles.logoutBtn} onClick={handleLogout} title="Cerrar sesión">
            ⏻
          </button>
        </div>
      </aside>

      {/* ── Main ────────────────────────────────────────────────────────── */}
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
