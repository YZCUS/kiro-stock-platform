"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  Home,
  List,
  LogOut,
  Menu,
  Server,
  Star,
  Target,
  User,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { useDialogA11y } from "@/hooks/useDialogA11y";
import { cn } from "@/lib/utils";
import { useAppDispatch, useAppSelector } from "@/store";
import { logout } from "@/store/slices/authSlice";

import MarketSearchCommand from "./MarketSearchCommand";

const publicLinks = [
  { href: "/", label: "首頁", icon: Home },
  { href: "/dashboard", label: "即時分析", icon: BarChart3 },
  { href: "/system", label: "系統狀態", icon: Server },
] as const;

const authedLinks = [
  { href: "/stocks", label: "股票工作區", icon: List },
  { href: "/strategies", label: "策略與信號", icon: Target },
  { href: "/portfolio", label: "投資組合", icon: Star },
] as const;

export default function Navigation() {
  const router = useRouter();
  const pathname = usePathname();
  const dispatch = useAppDispatch();
  const { initialized, isAuthenticated, user } = useAppSelector(
    (state) => state.auth,
  );
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const mobileMenuRef = useDialogA11y(isMobileMenuOpen, () =>
    setIsMobileMenuOpen(false),
  );

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [pathname, isAuthenticated]);

  useEffect(() => {
    if (!isMobileMenuOpen) return;

    const desktopQuery = window.matchMedia?.("(min-width: 1024px)");
    if (desktopQuery?.matches) {
      setIsMobileMenuOpen(false);
      return;
    }

    const handleViewportChange = (event: MediaQueryListEvent) => {
      if (event.matches) setIsMobileMenuOpen(false);
    };

    desktopQuery?.addEventListener("change", handleViewportChange);

    return () => {
      desktopQuery?.removeEventListener("change", handleViewportChange);
    };
  }, [isMobileMenuOpen]);

  const isActive = (href: string) =>
    href === "/"
      ? pathname === href
      : pathname === href || pathname.startsWith(`${href}/`);

  const currentPage = [...publicLinks, ...authedLinks].find((link) =>
    isActive(link.href),
  );

  const handleLogout = () => {
    dispatch(logout());
    setIsMobileMenuOpen(false);
    router.push("/");
  };

  const handleNavClick = (
    event: React.MouseEvent<HTMLAnchorElement>,
    href: string,
  ) => {
    setIsMobileMenuOpen(false);
    if (pathname === href) {
      event.preventDefault();
      router.refresh();
    }
  };

  return (
    <>
      <a
        href="#main-content"
        className="sr-only fixed left-4 top-3 z-[100] rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground focus:not-sr-only"
      >
        跳至主要內容
      </a>

      <aside className="fixed inset-y-0 left-0 z-50 hidden w-64 flex-col border-r border-border bg-card lg:flex">
        <div className="flex h-16 shrink-0 items-center border-b border-border px-5">
          <Link
            href="/"
            aria-label="股票分析平台"
            className="flex min-w-0 items-center gap-3 text-foreground transition-colors hover:text-primary"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-panel">
              <BarChart3 className="h-5 w-5" />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold tracking-tight">
                股票分析平台
              </span>
              <span className="block text-[11px] font-medium text-muted-foreground">
                Market Intelligence
              </span>
            </span>
          </Link>
        </div>

        <nav
          aria-label="主要導覽"
          className="flex min-h-0 flex-1 flex-col overflow-y-auto px-3 py-5"
        >
          <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            工作台
          </p>
          <div className="space-y-1">
            {publicLinks.map((link) => {
              const Icon = link.icon;
              const active = isActive(link.href);

              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={(event) => handleNavClick(event, link.href)}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex h-10 items-center gap-3 rounded-md border border-transparent px-3 text-sm font-medium transition-colors",
                    active
                      ? "border-primary/15 bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </div>

          {initialized && isAuthenticated && (
            <div className="mt-7">
              <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                個人資產
              </p>
              <div className="space-y-1">
                {authedLinks.map((link) => {
                  const Icon = link.icon;
                  const active = isActive(link.href);

                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      onClick={(event) => handleNavClick(event, link.href)}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "flex h-10 items-center gap-3 rounded-md border border-transparent px-3 text-sm font-medium transition-colors",
                        active
                          ? "border-primary/15 bg-primary/10 text-primary"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground",
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      <span>{link.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          )}

          <div className="mt-auto px-3 pt-8">
            <div className="rounded-lg border border-border bg-muted/60 p-3">
              <p className="text-xs font-medium text-foreground">
                Research workspace
              </p>
              <p className="mt-1 text-[11px] leading-4 text-muted-foreground">
                台股與美股的分析、策略與持倉集中管理。
              </p>
            </div>
          </div>
        </nav>
      </aside>

      <header className="fixed inset-x-0 top-0 z-40 flex h-16 items-center border-b border-border bg-card/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-card/90 sm:px-6 lg:left-64 lg:px-8">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <Link
            href="/"
            aria-label="返回首頁"
            className="flex min-w-0 items-center gap-2 text-foreground lg:hidden"
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <BarChart3 className="h-4 w-4" />
            </span>
            <span className="truncate text-sm font-semibold">股票分析平台</span>
          </Link>

          <div className="hidden min-w-0 lg:block">
            <p className="truncate text-sm font-semibold text-foreground">
              {currentPage ? `目前：${currentPage.label}` : "市場工作台"}
            </p>
            <p className="text-xs text-muted-foreground">
              即時市場資料與投資決策
            </p>
          </div>
        </div>

        <MarketSearchCommand />

        <div className="hidden items-center gap-2 lg:flex">
          <div className="mx-1 h-6 w-px bg-border" aria-hidden="true" />

          {!initialized ? (
            <div
              className="h-9 w-28 animate-pulse rounded-md bg-muted"
              aria-label="正在確認登入狀態"
            />
          ) : isAuthenticated ? (
            <div className="flex items-center gap-1.5">
              <div className="flex max-w-44 items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                  <User className="h-3.5 w-3.5" />
                </span>
                <span className="truncate">{user?.username}</span>
              </div>
              <Button
                variant="ghost"
                size="iconSm"
                onClick={handleLogout}
                aria-label="登出"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" asChild>
                <Link href="/login">登入</Link>
              </Button>
              <Button size="sm" asChild>
                <Link href="/register">註冊</Link>
              </Button>
            </div>
          )}
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="ml-2 lg:hidden"
          onClick={() => setIsMobileMenuOpen((open) => !open)}
          aria-label={isMobileMenuOpen ? "關閉導覽選單" : "開啟導覽選單"}
          aria-expanded={isMobileMenuOpen}
          aria-controls="mobile-navigation"
        >
          {isMobileMenuOpen ? (
            <X className="h-5 w-5" />
          ) : (
            <Menu className="h-5 w-5" />
          )}
        </Button>
      </header>

      {isMobileMenuOpen && (
        <div
          ref={mobileMenuRef}
          id="mobile-navigation"
          role="dialog"
          aria-modal="true"
          aria-label="導覽選單"
          tabIndex={-1}
          className="fixed inset-x-0 bottom-0 top-16 z-40 overflow-y-auto bg-background p-4 lg:hidden"
        >
          <nav aria-label="行動版導覽" className="mx-auto max-w-lg">
            <div className="rounded-lg border border-border bg-card p-2 shadow-panel">
              {publicLinks.map((link) => {
                const Icon = link.icon;
                const active = isActive(link.href);

                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={(event) => handleNavClick(event, link.href)}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex h-11 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors",
                      active
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {link.label}
                  </Link>
                );
              })}
            </div>

            {initialized && isAuthenticated && (
              <div className="mt-4 rounded-lg border border-border bg-card p-2 shadow-panel">
                <p className="px-3 pb-2 pt-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  個人資產
                </p>
                {authedLinks.map((link) => {
                  const Icon = link.icon;
                  const active = isActive(link.href);

                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      onClick={(event) => handleNavClick(event, link.href)}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "flex h-11 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors",
                        active
                          ? "bg-primary/10 text-primary"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground",
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      {link.label}
                    </Link>
                  );
                })}
              </div>
            )}

            <div className="mt-4 rounded-lg border border-border bg-card p-3 shadow-panel">
              {!initialized ? (
                <div
                  className="h-9 animate-pulse rounded-md bg-muted"
                  aria-label="正在確認登入狀態"
                />
              ) : isAuthenticated ? (
                <div className="flex items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                      <User className="h-4 w-4" />
                    </span>
                    <span className="truncate">{user?.username}</span>
                  </div>
                  <Button variant="outline" size="sm" onClick={handleLogout}>
                    <LogOut className="h-4 w-4" />
                    登出
                  </Button>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-2">
                  <Button variant="outline" size="sm" asChild>
                    <Link href="/login">登入</Link>
                  </Button>
                  <Button size="sm" asChild>
                    <Link href="/register">註冊</Link>
                  </Button>
                </div>
              )}
            </div>
          </nav>
        </div>
      )}
    </>
  );
}
