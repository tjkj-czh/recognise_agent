import { LandSupply } from '@/services/api'
import { MapPin, Ruler, Tag, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDate } from '@/utils/date'

interface LandSupplyCardProps {
  data: LandSupply
  isSelected?: boolean
  onClick?: () => void
}

const stageColors: Record<string, string> = {
  '已成交': 'bg-green-100 text-green-700',
  '挂牌中': 'bg-blue-100 text-blue-700',
  '公告中': 'bg-amber-100 text-amber-700',
  '流拍': 'bg-red-100 text-red-700',
}

export default function LandSupplyCard({ data, isSelected, onClick }: LandSupplyCardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'p-4 rounded-xl border cursor-pointer transition-all duration-200 hover:shadow-md',
        isSelected
          ? 'bg-blue-50 border-blue-300 shadow-md'
          : 'bg-white border-slate-200 hover:border-blue-200'
      )}
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-semibold text-slate-800 text-sm leading-tight pr-2">
          {data.plotName}
        </h3>
        <span
          className={cn(
            'shrink-0 text-xs px-2 py-0.5 rounded-full font-medium',
            stageColors[data.transactionStage] || 'bg-slate-100 text-slate-600'
          )}
        >
          {data.transactionStage}
        </span>
      </div>

      <div className="flex items-center gap-1 text-xs text-slate-500 mb-2">
        <MapPin className="w-3 h-3" />
        <span>{data.district}</span>
        <span className="mx-1">·</span>
        <Tag className="w-3 h-3" />
        <span>{data.landUseType}</span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center gap-1 text-slate-600">
          <Ruler className="w-3 h-3 text-slate-400" />
          <span>{data.areaSqm.toLocaleString()} m²</span>
        </div>
        <div className="flex items-center gap-1 text-slate-600">
          <span className="text-slate-400">亩</span>
          <span>{data.areaMu} 亩</span>
        </div>
        {data.startingPrice && (
          <div className="flex items-center gap-1 text-slate-600">
            <span className="text-slate-400">起</span>
            <span>{(data.startingPrice / 10000).toFixed(1)}亿</span>
          </div>
        )}
        {data.transactionPrice && (
          <div className="flex items-center gap-1 text-slate-600">
            <span className="text-slate-400">成</span>
            <span>{(data.transactionPrice / 10000).toFixed(1)}亿</span>
          </div>
        )}
        {data.transactionDate && (
          <div className="flex items-center gap-1 text-slate-600 col-span-2">
            <Clock className="w-3 h-3 text-slate-400" />
            <span>成交 {formatDate(data.transactionDate)}</span>
          </div>
        )}
      </div>

      {data.plotRatio && (
        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center gap-2 text-xs text-slate-500">
          <span>容积率 {data.plotRatio}</span>
          <span>·</span>
          <span>编号 {data.transferNo}</span>
        </div>
      )}
    </div>
  )
}
