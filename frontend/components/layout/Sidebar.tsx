'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { UserButton } from '@clerk/nextjs';
import {
  LayoutDashboard,
  Radio,
  TrendingUp,
  Users,
  Search,
  FileText,
  ClipboardCheck,
  Database,
  Network,
  BookOpen,
  BarChart3,
  Bell,
  ChevronRight,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAlerts } from '@/lib/api';

// ─── Nav Items ────────────────────────────────────────────────

const NAV_SECTIONS = [
  {
    label: 'Intelligence',
    items: [
      { href: '/',              icon: LayoutDashboard, label: 'Executive Portal'  },
      { href: '/intelligence',  icon: Database,        label: 'Market Explorer'   },
      { href: '/signals',       icon: Zap,             label: 'Signals'           },
      { href: '/trends',        icon: TrendingUp,      label: 'Trends'            },
      { href: '/competitors',   icon: Users,           label: 'Competitors'       },
    ],
  },
  {
    label: 'Content & Review',
    items: [
      { href: '/content',  icon: FileText,      label: 'Content Strategy'  },
      { href: '/review',   icon: ClipboardCheck, label: 'Review Queue'     },
      { href: '/search',   icon: Search,         label: 'Advanced Search'  },
    ],
  },
  {
    label: 'Knowledge',
    items: [
      { href: '/repository', icon: Database,   label: 'Repository'      },
      { href: '/graph',      icon: Network,    label: 'Knowledge Graph' },
      { href: '/executive',  icon: BookOpen,   label: 'Briefings'       },
      { href: '/analytics',  icon: BarChart3,  label: 'ROI Dashboard'   },
    ],
  },
];

// ─── NavItem ─────────────────────────────────────────────────

interface NavItemProps {
  href: string;
  icon: React.ElementType;
  label: string;
  badge?: number;
  collapsed?: boolean;
}

function NavItem({ href, icon: Icon, label, badge, collapsed }: NavItemProps) {
  const pathname = usePathname();
  const isActive = pathname === href || (href !== '/' && pathname.startsWith(href));

  return (
    <Link
      href={href}
      className={cn(
        'group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all duration-150',
        isActive
          ? 'bg-brand-500/20 text-brand-300 border border-brand-500/30'
          : 'text-muted-foreground hover:bg-surface-elevated hover:text-foreground border border-transparent'
      )}
    >
      <Icon
        className={cn(
          'h-4 w-4 shrink-0 transition-colors',
          isActive ? 'text-brand-400' : 'text-muted-foreground group-hover:text-foreground'
        )}
      />
      {!collapsed && (
        <>
          <span className="flex-1 truncate">{label}</span>
          {badge !== undefined && badge > 0 && (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-brand-500 text-[10px] font-bold text-white">
              {badge > 99 ? '99+' : badge}
            </span>
          )}
          {isActive && (
            <ChevronRight className="h-3 w-3 text-brand-400" />
          )}
        </>
      )}
    </Link>
  );
}

// ─── Sidebar ─────────────────────────────────────────────────

export function Sidebar() {
  const { data: alerts } = useAlerts(true);
  const unreadAlerts = alerts?.length ?? 0;

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-surface-border bg-surface-elevated">
      {/* Logo / Brand */}
      <div className="flex h-16 items-center gap-3 border-b border-surface-border px-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-signal">
          <Zap className="h-4 w-4 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold text-foreground tracking-wider">TADA</p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Intelligence</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto scrollbar-thin py-4 px-3 space-y-6">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
              {section.label}
            </p>
            <ul className="space-y-1">
              {section.items.map((item) => (
                <li key={item.href}>
                  <NavItem {...item} />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* Bottom: Alerts + User */}
      <div className="border-t border-surface-border p-3 space-y-1">
        <NavItem
          href="/alerts"
          icon={Bell}
          label="Notifications"
          badge={unreadAlerts}
        />
        <div className="flex items-center gap-3 rounded-md px-3 py-2">
          <UserButton
            appearance={{
              elements: {
                avatarBox: 'h-7 w-7',
              },
            }}
          />
          <span className="text-xs text-muted-foreground">Account</span>
        </div>
      </div>
    </aside>
  );
}
