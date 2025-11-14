'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useAppSelector, useAppDispatch } from '@/store';
import { logout } from '@/store/slices/authSlice';
import { Button } from '@/components/ui/button';
import { BarChart3, Star, User, LogOut, Target } from 'lucide-react';
import WebSocketStatus from './ui/WebSocketStatus';

export default function Navigation() {
  const router = useRouter();
  const pathname = usePathname();
  const dispatch = useAppDispatch();
  const { isAuthenticated, user } = useAppSelector((state) => state.auth);

  const handleLogout = () => {
    dispatch(logout());
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
    <nav className="bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link href="/" className="flex items-center gap-2 text-xl font-bold text-gray-900 hover:text-blue-600 transition-colors">
              <BarChart3 className="w-6 h-6" />
              股票分析平台
            </Link>
          </div>
          <div className="flex items-center space-x-1">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/" onClick={(e) => handleNavClick(e, '/')}>首頁</Link>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/stocks" onClick={(e) => handleNavClick(e, '/stocks')}>股票管理</Link>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/dashboard" onClick={(e) => handleNavClick(e, '/dashboard')}>即時分析</Link>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/signals" onClick={(e) => handleNavClick(e, '/signals')}>交易信號</Link>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/system" onClick={(e) => handleNavClick(e, '/system')}>系統狀態</Link>
            </Button>

            {isAuthenticated ? (
              <>
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/strategies" onClick={(e) => handleNavClick(e, '/strategies')} className="flex items-center gap-1">
                    <Target className="w-4 h-4" />
                    策略中心
                  </Link>
                </Button>
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/portfolio" onClick={(e) => handleNavClick(e, '/portfolio')} className="flex items-center gap-1">
                    <Star className="w-4 h-4" />
                    持倉管理
                  </Link>
                </Button>
                <div className="border-l border-gray-300 ml-2 pl-2 flex items-center gap-2">
                  <div className="flex items-center gap-1 text-sm text-gray-700">
                    <User className="w-4 h-4" />
                    {user?.username}
                  </div>
                  <Button variant="ghost" size="sm" onClick={handleLogout}>
                    <LogOut className="w-4 h-4" />
                  </Button>
                </div>
              </>
            ) : (
              <div className="border-l border-gray-300 ml-2 pl-2 flex items-center gap-2">
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/login">登入</Link>
                </Button>
                <Button variant="default" size="sm" asChild>
                  <Link href="/register">註冊</Link>
                </Button>
              </div>
            )}

            {/* WebSocket Status */}
            <div className="border-l border-gray-300 ml-4 pl-4">
              <WebSocketStatus />
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
