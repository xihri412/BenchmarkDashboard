import type { ReactNode } from "react";

import type { AppRoute } from "../router/routes";
import { routes } from "../router/routes";

type AppLayoutProps = {
  activeRoute: AppRoute;
  children: ReactNode;
  onNavigate: (path: string) => void;
};

export function AppLayout({ activeRoute, children, onNavigate }: AppLayoutProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">BD</span>
          <div>
            <p className="brand-name">评测</p>
            <p className="brand-subtitle">看板</p>
          </div>
        </div>

        <nav className="nav-list" aria-label="主导航">
          {routes.map((route) => (
            <button
              key={route.id}
              className={`nav-item ${
                route.id === activeRoute.id ? "is-active" : ""
              }`}
              type="button"
              onClick={() => onNavigate(route.path)}
            >
              {route.label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="content">{children}</main>
    </div>
  );
}
