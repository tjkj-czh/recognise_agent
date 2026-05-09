import { useEffect, useRef, useCallback } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { LandSupply } from '@/services/api'

interface HangzhouMapProps {
  landSupplies: LandSupply[]
  selectedId?: number | null
  onSelect?: (id: number) => void
}

export default function HangzhouMap({ landSupplies, selectedId, onSelect }: HangzhouMapProps) {
  const mapRef = useRef<L.Map | null>(null)
  const markersRef = useRef<Record<number, L.Marker>>({})
  const containerRef = useRef<HTMLDivElement>(null)

  const initMap = useCallback(() => {
    if (!containerRef.current || mapRef.current) return

    const map = L.map(containerRef.current, {
      center: [30.2741, 120.1551],
      zoom: 11,
      zoomControl: false,
    })

    L.control.zoom({ position: 'bottomright' }).addTo(map)

    // 高德瓦片图层
    L.tileLayer(
      'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
      {
        subdomains: '1234',
        attribution: '© 高德地图',
      }
    ).addTo(map)

    mapRef.current = map
  }, [])

  useEffect(() => {
    initMap()
    return () => {
      mapRef.current?.remove()
      mapRef.current = null
      markersRef.current = {}
    }
  }, [initMap])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    // Clear existing markers
    Object.values(markersRef.current).forEach((m) => map.removeLayer(m))
    markersRef.current = {}

    landSupplies.forEach((item) => {
      const isSelected = selectedId === item.id
      const iconHtml = `
        <div class="relative flex items-center justify-center">
          <div class="w-4 h-4 rounded-full ${isSelected ? 'bg-blue-500 ring-4 ring-blue-500/30' : 'bg-cyan-500'} border-2 border-white shadow-lg transition-all duration-300"></div>
        </div>
      `

      const icon = L.divIcon({
        html: iconHtml,
        className: 'custom-marker',
        iconSize: [20, 20],
        iconAnchor: [10, 10],
      })

      const marker = L.marker([item.latitude, item.longitude], { icon }).addTo(map)

      const popupContent = `
        <div style="font-family: system-ui, sans-serif; min-width: 200px;">
          <h3 style="font-weight: 700; color: #1e293b; font-size: 0.875rem; margin-bottom: 4px;">${item.plotName}</h3>
          <p style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px;">${item.district} · ${item.landUseType}</p>
          <div style="display: flex; gap: 8px; font-size: 0.75rem;">
            <span style="background: #eff6ff; color: #1d4ed8; padding: 2px 8px; border-radius: 4px;">${item.areaMu}亩</span>
            <span style="background: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 4px;">${item.transactionStage}</span>
          </div>
        </div>
      `

      marker.bindPopup(popupContent)
      marker.on('click', () => onSelect?.(item.id))
      markersRef.current[item.id] = marker
    })
  }, [landSupplies, selectedId, onSelect])

  // Fly to selected item
  useEffect(() => {
    const map = mapRef.current
    if (!map || !selectedId) return
    const item = landSupplies.find((l) => l.id === selectedId)
    if (item) {
      map.flyTo([item.latitude, item.longitude], 14, { duration: 1 })
      const marker = markersRef.current[selectedId]
      if (marker) marker.openPopup()
    }
  }, [selectedId, landSupplies])

  return <div ref={containerRef} className="w-full h-full" />
}
