'use client';

import { StockDetailPage } from '../../../components/StockManagement';

interface StockDetailPageProps {
    params: {
        id: string;
    };
}

export default function StockDetail({ params }: StockDetailPageProps) {
    const stockId = parseInt(params.id);
    return <StockDetailPage stockId={stockId} />;
}