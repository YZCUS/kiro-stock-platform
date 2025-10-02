/**
 * 股票管理頁面 Loading UI
 */
export default function StocksLoading() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="animate-pulse">
        {/* 標題 skeleton */}
        <div className="h-8 bg-gray-200 rounded w-48 mb-6"></div>

        {/* 表格 skeleton */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="space-y-4">
            <div className="h-4 bg-gray-200 rounded w-full"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
            <div className="h-4 bg-gray-200 rounded w-4/6"></div>
            <div className="h-4 bg-gray-200 rounded w-full"></div>
            <div className="h-4 bg-gray-200 rounded w-3/6"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
