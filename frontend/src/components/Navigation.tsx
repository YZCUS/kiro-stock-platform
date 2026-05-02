'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useAppSelector, useAppDispatch } from '@/store';
import { logout } from '@/store/slices/authSlice';
import { Button } from '@/components/ui/button';
import { BarChart3, Star, User, LogOut, Target, Menu, X } from 'lucide-react';
import WebSocketStatus from './ui/WebSocketStatus';
import MarketSearchCommand from './MarketSearchCommand';

const publicLinks = [
  { href: '/', label: '首頁' },
  { href: '/stocks', label: '股票管理' },
  { href: '/dashboard', label: '即時分析' },
  { href: '/signals', label: '交易信號' },
  { href: '/system', label: '系統狀態' },
];

const authedLinks = [
  { href: '/strategies', label: '策略中心', icon: Target },
  { href: '/portfolio', label: '持倉管理', icon: Star },
];

export default function Navigation() {
  const router = useRouter();
  const pathname = usePathname();
  const dispatch = useAppDispatch();
  const { isAuthenticated, user } = useAppSelector((state) => state.auth);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [pathname, isAuthenticated]);

  const handleLogout = () => {
    dispatch(logout());
    setIsMobileMenuOpen(false);
    router.push('/');
  };

  // Handle navigation with refresh on same page click
  const handleNavClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (pathname === href) {
      e.preventDefault();
      router.refresh();
    }
  };

  return (
    <nav className="sticky top-0 z-50 border-b border-gray-200 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex min-w-0 items-center">
            <Link href="/" className="flex min-w-0 items-center gap-2 text-base font-semibold text-gray-900 transition-colors hover:text-gray-700 sm:text-lg">
              <BarChart3 className="w-6 h-6" />
              <span className="truncate">股票分析平台</span>
            </Link>
          </div>
          <div className="hidden items-center space-x-1 lg:flex">
            <MarketSearchCommand />
            {publicLinks.map((link) => (
              <Button
                key={link.href}
                variant={pathname === link.href ? 'secondary' : 'ghost'}
                size="sm"
                asChild
              >
                <Link href={link.href} onClick={(e) => handleNavClick(e, link.href)}>
                  {link.label}
                </Link>
              </Button>
            ))}

            {isAuthenticated ? (
              <>
                {authedLinks.map((link) => {
                  const Icon = link.icon;
                  return (
                    <Button
                      key={link.href}
                      variant={pathname === link.href ? 'secondary' : 'ghost'}
                      size="sm"
                      asChild
                    >
                      <Link href={link.href} onClick={(e) => handleNavClick(e, link.href)} className="flex items-center gap-1">
                        <Icon className="w-4 h-4" />
                        {link.label}
                      </Link>
                    </Button>
                  );
                })}
                <div className="ml-2 flex items-center gap-2 border-l border-gray-200 pl-2">
                  <div className="flex max-w-32 items-center gap-1 truncate text-sm text-gray-700">
                    <User className="w-4 h-4 flex-shrink-0" />
                    <span className="truncate">{user?.username}</span>
                  </div>
                  <Button variant="ghost" size="icon" onClick={handleLogout} aria-label="登出">
                    <LogOut className="w-4 h-4" />
                  </Button>
                </div>
              </>
            ) : (
              <div className="border-l border-gray-200 ml-2 pl-2 flex items-center gap-2">
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/login">登入</Link>
                </Button>
                <Button variant="default" size="sm" asChild>
                  <Link href="/register">註冊</Link>
                </Button>
              </div>
            )}

            <div className="ml-4 hidden border-l border-gray-200 pl-4 xl:block">
              <WebSocketStatus />
            </div>
          </div>

          <div className="flex items-center lg:hidden">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsMobileMenuOpen((open) => !open)}
              aria-label={isMobileMenuOpen ? '關閉導覽選單' : '開啟導覽選單'}
              aria-expanded={isMobileMenuOpen}
            >
              {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </Button>
          </div>
        </div>

        {isMobileMenuOpen && (
          <div className="border-t border-gray-200 py-3 lg:hidden">
            <div className="grid gap-1">
              {publicLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={(e) => handleNavClick(e, link.href)}
                  className={`rounded-md px-3 py-2 text-sm font-medium ${
                    pathname === link.href
                      ? 'bg-gray-100 text-gray-900'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  {link.label}
                </Link>
              ))}

              {isAuthenticated ? (
                <>
                  {authedLinks.map((link) => {
                    const Icon = link.icon;
                    return (
                      <Link
                        key={link.href}
                        href={link.href}
                        onClick={(e) => handleNavClick(e, link.href)}
                        className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${
                          pathname === link.href
                            ? 'bg-gray-100 text-gray-900'
                            : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                        {link.label}
                      </Link>
                    );
                  })}
                  <div className="mt-2 border-t border-gray-200 pt-3">
                    <div className="mb-2 flex items-center gap-2 px-3 text-sm text-gray-600">
                      <User className="h-4 w-4" />
                      <span className="truncate">{user?.username}</span>
                    </div>
                    <Button variant="outline" size="sm" onClick={handleLogout} className="w-full justify-center">
                      <LogOut className="h-4 w-4" />
                      登出
                    </Button>
                  </div>
                </>
              ) : (
                <div className="mt-2 grid grid-cols-2 gap-2 border-t border-gray-200 pt-3">
                  <Button variant="outline" size="sm" asChild>
                    <Link href="/login">登入</Link>
                  </Button>
                  <Button size="sm" asChild>
                    <Link href="/register">註冊</Link>
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
