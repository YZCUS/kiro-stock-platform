/**
 * 圖表分析頁面 Loading UI
 */
export default function ChartsLoading() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-48 mb-6"></div>

        {/* 圖表容器 skeleton */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="h-96 bg-gray-200 rounded mb-4"></div>
          <div className="grid grid-cols-4 gap-4">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
