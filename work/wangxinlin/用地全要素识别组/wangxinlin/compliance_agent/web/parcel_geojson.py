"""生成杭州市模拟图斑GeoJSON数据。"""

import json
import math
import random

# 杭州市各区域的图斑中心坐标
PARCEL_CENTERS = [
    (120.050, 30.300),  # P20240101 余杭区 - 耕地为主
    (120.150, 30.330),  # P20240102 拱墅区 - 建设用地为主
    (120.130, 30.240),  # P20240103 西湖区 - 水体为主
]

# 为了在地图上可见，多边形半径需要放大（模拟遥感图斑在宏观地图上的展示）
# 基础半径约0.008度（约800m），面积大的图斑略大
BASE_RADIUS = 0.008


def _make_irregular_polygon(center_lon: float, center_lat: float, area_m2: float,
                            num_vertices: int = 8, seed: int = 42) -> list[list[float]]:
    """根据中心点和面积生成不规则多边形坐标。"""
    rng = random.Random(seed)
    # 按面积比例缩放半径，使大图斑在地图上略大
    scale = math.sqrt(area_m2 / 10000)  # 以10000m2为基准
    radius = BASE_RADIUS * min(max(scale, 0.6), 1.5)

    coords = []
    for i in range(num_vertices):
        angle = 2 * math.pi * i / num_vertices
        jitter = 0.75 + rng.random() * 0.5  # 0.75~1.25 的随机抖动
        lon = center_lon + radius * math.cos(angle) * jitter
        lat = center_lat + radius * (0.85 + rng.random() * 0.3) * math.sin(angle) * jitter
        coords.append([round(lon, 6), round(lat, 6)])

    coords.append(coords[0])  # 闭合多边形
    return coords


def generate_parcels_geojson(parcels_data: list[dict]) -> dict:
    """为所有图斑生成GeoJSON FeatureCollection。"""
    features = []
    for i, parcel in enumerate(parcels_data):
        if i >= len(PARCEL_CENTERS):
            break
        center_lon, center_lat = PARCEL_CENTERS[i]
        coords = _make_irregular_polygon(
            center_lon, center_lat,
            parcel["total_area_m2"],
            seed=i * 100 + 7
        )
        feature = {
            "type": "Feature",
            "properties": {
                "parcel_id": parcel["parcel_id"],
                "location": parcel["location"],
                "total_area_m2": parcel["total_area_m2"],
                "dominant_type": parcel["dominant_type"],
                "is_mixed": parcel["is_mixed"],
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords],
            }
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


if __name__ == "__main__":
    import os
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    with open(os.path.join(data_dir, "sample_parcels.json"), "r", encoding="utf-8") as f:
        parcels = json.load(f)

    geojson = generate_parcels_geojson(parcels)
    out_path = os.path.join(data_dir, "parcels.geojson")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    print(f"Generated {len(geojson['features'])} parcels -> {out_path}")
