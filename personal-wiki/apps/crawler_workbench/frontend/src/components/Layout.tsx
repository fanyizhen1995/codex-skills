import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import type { PageKey } from "../types";

export interface NavigationItem {
  key: PageKey;
  label: string;
  icon: LucideIcon;
}

interface LayoutProps {
  activePage: PageKey;
  navigation: NavigationItem[];
  onNavigate: (page: PageKey) => void;
  children: ReactNode;
}

export function Layout({ activePage, navigation, onNavigate, children }: LayoutProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand">
          <div className="brand-mark">PW</div>
          <div>
            <div className="brand-title">Crawler Workbench</div>
            <div className="brand-subtitle">Personal Wiki</div>
          </div>
        </div>
        <nav className="nav-list">
          {navigation.map((item) => {
            const Icon = item.icon;
            const active = item.key === activePage;
            return (
              <button
                key={item.key}
                className={`nav-button${active ? " active" : ""}`}
                type="button"
                aria-current={active ? "page" : undefined}
                onClick={() => onNavigate(item.key)}
              >
                <Icon aria-hidden="true" size={17} strokeWidth={2} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
