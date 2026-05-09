"""生成浙江省地类分割GeoJSON数据。

从阿里云DataV获取区县级行政边界，根据地理规则为每个区县分配
主导地类（耕地、建设用地、水体、林地、草地），模拟AI遥感识别结果。
"""

import json
import math
import os
import urllib.request

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "land_segments.geojson")

DATAV_URL = "https://geo.datav.aliyun.com/areas_v3/bound/330000_full.json"

# ── 地类分配规则 ──────────────────────────────────────────────

# 水体：舟山全境、沿海区县、千岛湖
WATER_CODES = {
    "330900",  # 舟山市（整体）
    "330902", "330903", "330921", "330922",  # 舟山区县
    "330206",  # 北仑区（沿海）
    "330211",  # 镇海区（沿海）
    "330283",  # 奉化区（沿海）
    "330281",  # 余姚市东部近海
    "330127",  # 淳安县（千岛湖）
    "330326",  # 平阳县（沿海）
    "330327",  # 苍南县（沿海）
    "330381",  # 瑞安市（沿海）
    "330382",  # 乐清市（沿海）
    "330682",  # 上虞区（近杭州湾）
    "331082",  # 临海市（沿海）
    "331003",  # 黄岩区（近海）
    "331004",  # 路桥区（沿海）
    "330402",  # 南湖区（近太湖）
    "330411",  # 秀洲区（近太湖）
}

# 建设用地：核心城区
CONSTRUCTION_CODES = {
    "330102",  # 上城区
    "330105",  # 拱墅区
    "330106",  # 西湖区
    "330108",  # 滨江区
    "330113",  # 临平区
    "330114",  # 钱塘区
    "330203",  # 海曙区
    "330205",  # 江北区
    "330212",  # 鄞州区
    "330302",  # 鹿城区
    "330303",  # 龙湾区
    "330304",  # 瓯海区
    "330602",  # 越城区
    "330702",  # 婺城区
    "330703",  # 金东区
    "330802",  # 柯城区
    "330803",  # 衢江区
    "331002",  # 椒江区
}

# 林地：山区
FOREST_CODES = {
    # 丽水全境
    "331102", "331121", "331122", "331123", "331124", "331125", "331126", "331127", "331181",
    # 衢州山区县
    "330822",  # 常山县
    "330824",  # 开化县
    "330825",  # 龙游县
    "330881",  # 江山市
    # 杭州西部山区
    "330112",  # 临安区
    "330122",  # 桐庐县
    "330182",  # 建德市
    "330185",  # 淳安已归水体
    # 温州山区
    "330324",  # 永嘉县
    "330328",  # 文成县
    "330329",  # 泰顺县
    # 绍兴山区
    "330623",  # 新昌县
    # 台州山区
    "331023",  # 天台县
    "331024",  # 仙居县
    "331081",  # 温岭市已归其他
    # 宁波山区
    "330226",  # 宁海县
    "330227",  # 象山县
    # 湖州山区
    "330523",  # 安吉县
}

# 草地：过渡带
GRASSLAND_CODES = {
    "330681",  # 诸暨市
    "330782",  # 义乌市
    "330783",  # 东阳市
    "330784",  # 永康市
    "330781",  # 兰溪市
    "330521",  # 德清县
    "330111",  # 富阳区
    "330624",  # 嵊州市
    "331083",  # 温岭市
    "330322",  # 洞头区
}

# 耕地：平原（默认，未匹配的平原区县）


def _centroid(geometry: dict) -> tuple:
    """计算多边形质心（简易版）。"""
    coords = geometry.get("coordinates", [])
    if not coords:
        return (0, 0)

    flat = []
    for ring in coords:
        if isinstance(ring[0], (int, float)):
            flat = coords
            break
        for pt in ring:
            if isinstance(pt[0], (int, float)):
                flat.append(pt)
            else:
                for p in pt:
                    if isinstance(p[0], (int, float)):
                        flat.append(p)

    if not flat:
        return (0, 0)

    lons = [p[0] for p in flat if isinstance(p[0], (int, float))]
    lats = [p[1] for p in flat if isinstance(p[1], (int, float))]
    if not lons:
        return (0, 0)
    return (sum(lons) / len(lons), sum(lats) / len(lats))


def _is_coastal(adcode: str, lon: float, lat: float) -> bool:
    """判断区县是否沿海。"""
    # 浙北海岸线约 lon > 121.5
    if lat > 29.5 and lon > 121.3:
        return True
    # 浙南海岸线
    if lat <= 29.5 and lon > 120.8:
        return True
    return False


def _simplify_ring(ring: list, tolerance: float = 0.01) -> list:
    """Douglas-Peucker简化多边形环。"""
    if len(ring) <= 3:
        return ring

    # 找到最大偏差点
    start, end = ring[0], ring[-1]
    max_dist = 0
    max_idx = 0

    for i in range(1, len(ring) - 1):
        dist = _point_line_distance(ring[i], start, end)
        if dist > max_dist:
            max_dist = dist
            max_idx = i

    if max_dist > tolerance:
        left = _simplify_ring(ring[:max_idx + 1], tolerance)
        right = _simplify_ring(ring[max_idx:], tolerance)
        return left[:-1] + right
    else:
        return [start, end]


def _point_line_distance(point: list, line_start: list, line_end: list) -> float:
    """点到线段的距离。"""
    px, py = point[0], point[1]
    x1, y1 = line_start[0], line_start[1]
    x2, y2 = line_end[0], line_end[1]

    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    proj_x, proj_y = x1 + t * dx, y1 + t * dy
    return math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)


def _simplify_geometry(geometry: dict, tolerance: float = 0.01) -> dict:
    """简化GeoJSON几何。"""
    geom_type = geometry.get("type", "")
    coords = geometry.get("coordinates", [])

    if geom_type == "Polygon":
        new_coords = []
        for ring in coords:
            new_ring = _simplify_ring(ring, tolerance)
            if len(new_ring) >= 3:
                new_coords.append(new_ring)
        return {"type": geom_type, "coordinates": new_coords}

    elif geom_type == "MultiPolygon":
        new_polys = []
        for poly in coords:
            new_rings = []
            for ring in poly:
                new_ring = _simplify_ring(ring, tolerance)
                if len(new_ring) >= 3:
                    new_rings.append(new_ring)
            if new_rings:
                new_polys.append(new_rings)
        return {"type": geom_type, "coordinates": new_polys}

    return geometry


def assign_land_type(adcode: str, name: str, lon: float, lat: float) -> tuple:
    """为区县分配地类和置信度。返回 (地类, 置信度)。"""
    code_prefix = adcode[:4] if len(adcode) >= 4 else adcode

    # 1. 水体优先
    if adcode in WATER_CODES or _is_coastal(adcode, lon, lat):
        # 排除已明确为建设用地的
        if adcode in CONSTRUCTION_CODES:
            pass
        else:
            return ("水体", 0.82 if _is_coastal(adcode, lon, lat) else 0.88)

    # 2. 建设用地
    if adcode in CONSTRUCTION_CODES:
        return ("建设用地", 0.91)

    # 3. 林地
    if adcode in FOREST_CODES:
        return ("林地", 0.87)

    # 4. 草地
    if adcode in GRASSLAND_CODES:
        return ("草地", 0.78)

    # 5. 耕地（默认：嘉兴、湖州、绍兴平原等）
    farmland_prefixes = {"3304", "3305"}  # 嘉兴、湖州
    if code_prefix in farmland_prefixes:
        return ("耕地", 0.90)

    # 6. 其余按纬度/经度粗判
    if lon < 120.0 and lat > 29.0:
        return ("林地", 0.75)
    if lon < 120.3 and lat > 28.5:
        return ("草地", 0.72)

    return ("耕地", 0.76)


def _get_city_name(adcode: str) -> str:
    """根据区县代码推断所属地级市。"""
    city_map = {
        "3301": "杭州市", "3302": "宁波市", "3303": "温州市",
        "3304": "嘉兴市", "3305": "湖州市", "3306": "绍兴市",
        "3307": "金华市", "3308": "衢州市", "3309": "舟山市",
        "3310": "台州市", "3311": "丽水市",
    }
    return city_map.get(adcode[:4], "浙江省")


def fetch_datav() -> dict:
    """从DataV获取浙江省区县边界（逐市请求）。"""
    # 先获取省级数据获取市列表
    print(f"[DataV] 请求省级数据 {DATAV_URL} ...")
    req = urllib.request.Request(DATAV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        prov_data = json.loads(resp.read().decode("utf-8"))

    city_codes = []
    for feat in prov_data.get("features", []):
        adcode = str(feat.get("properties", {}).get("adcode", ""))
        if adcode and adcode != "330000":
            city_codes.append(adcode)

    print(f"[DataV] 找到 {len(city_codes)} 个地级市，逐市获取区县...")

    all_features = []
    for city_code in city_codes:
        url = f"https://geo.datav.aliyun.com/areas_v3/bound/{city_code}_full.json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                city_data = json.loads(resp.read().decode("utf-8"))
            city_features = city_data.get("features", [])
            # 跳过市级整体（只保留区县）
            for feat in city_features:
                level = feat.get("properties", {}).get("level", "")
                if level != "city":
                    all_features.append(feat)
            print(f"  {city_code}: {len(city_features)} features")
        except Exception as e:
            print(f"  {city_code}: 获取失败 ({e})")

    print(f"[DataV] 共获取 {len(all_features)} 个区县")
    return {"type": "FeatureCollection", "features": all_features}


def generate_fallback() -> dict:
    """离线fallback：用简化的11市多边形生成地类数据。"""
    features = []

    city_data = [
        {"code": "330100", "name": "杭州市", "type": "建设用地", "conf": 0.85,
         "coords": [[[119.7,29.9],[120.5,29.9],[120.5,30.6],[119.7,30.6],[119.7,29.9]]]},
        {"code": "330200", "name": "宁波市", "type": "建设用地", "conf": 0.83,
         "coords": [[[121.0,29.5],[122.2,29.5],[122.2,30.2],[121.0,30.2],[121.0,29.5]]]},
        {"code": "330300", "name": "温州市", "type": "水体", "conf": 0.80,
         "coords": [[[119.8,27.5],[121.2,27.5],[121.2,28.5],[119.8,28.5],[119.8,27.5]]]},
        {"code": "330400", "name": "嘉兴市", "type": "耕地", "conf": 0.92,
         "coords": [[[120.3,30.5],[121.2,30.5],[121.2,31.0],[120.3,31.0],[120.3,30.5]]]},
        {"code": "330500", "name": "湖州市", "type": "耕地", "conf": 0.88,
         "coords": [[[119.3,30.5],[120.3,30.5],[120.3,31.2],[119.3,31.2],[119.3,30.5]]]},
        {"code": "330600", "name": "绍兴市", "type": "耕地", "conf": 0.86,
         "coords": [[[120.0,29.3],[120.9,29.3],[120.9,30.0],[120.0,30.0],[120.0,29.3]]]},
        {"code": "330700", "name": "金华市", "type": "草地", "conf": 0.77,
         "coords": [[[119.3,28.7],[120.5,28.7],[120.5,29.6],[119.3,29.6],[119.3,28.7]]]},
        {"code": "330800", "name": "衢州市", "type": "林地", "conf": 0.85,
         "coords": [[[118.0,28.3],[119.3,28.3],[119.3,29.5],[118.0,29.5],[118.0,28.3]]]},
        {"code": "330900", "name": "舟山市", "type": "水体", "conf": 0.90,
         "coords": [[[121.6,29.8],[122.5,29.8],[122.5,30.3],[121.6,30.3],[121.6,29.8]]]},
        {"code": "331000", "name": "台州市", "type": "水体", "conf": 0.79,
         "coords": [[[120.5,28.3],[121.6,28.3],[121.6,29.3],[120.5,29.3],[120.5,28.3]]]},
        {"code": "331100", "name": "丽水市", "type": "林地", "conf": 0.89,
         "coords": [[[118.7,27.5],[120.2,27.5],[120.2,28.7],[118.7,28.7],[118.7,27.5]]]},
    ]

    for city in city_data:
        features.append({
            "type": "Feature",
            "properties": {
                "district_code": city["code"],
                "district_name": city["name"],
                "city_name": city["name"],
                "land_type": city["type"],
                "confidence": city["conf"],
            },
            "geometry": {"type": "Polygon", "coordinates": city["coords"]},
        })

    return {"type": "FeatureCollection", "features": features}


def generate_land_segments():
    """主函数：生成地类分割GeoJSON。"""
    try:
        datav_data = fetch_datav()
        features = datav_data.get("features", [])

        if not features:
            raise ValueError("DataV返回空数据")

        output_features = []
        for feat in features:
            props = feat.get("properties", {})
            adcode = str(props.get("adcode", ""))
            name = props.get("name", "")
            geometry = feat.get("geometry", {})

            if not adcode or not geometry:
                continue

            # 跳过省级和市级整体（只保留区县级）
            level = props.get("level", "")
            if level == "province":
                continue

            lon, lat = _centroid(geometry)
            land_type, confidence = assign_land_type(adcode, name, lon, lat)
            city_name = _get_city_name(adcode)

            simplified_geom = _simplify_geometry(geometry, tolerance=0.008)

            output_features.append({
                "type": "Feature",
                "properties": {
                    "district_code": adcode,
                    "district_name": name,
                    "city_name": city_name,
                    "land_type": land_type,
                    "confidence": round(confidence, 2),
                },
                "geometry": simplified_geom,
            })

        result = {"type": "FeatureCollection", "features": output_features}
        print(f"[生成] 区县级地类分割完成，共 {len(output_features)} 个区县")

    except Exception as e:
        print(f"[警告] DataV获取失败({e})，使用离线fallback数据")
        result = generate_fallback()

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)

    size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    print(f"[输出] {OUTPUT_PATH} ({size_kb:.0f} KB)")

    # 统计地类分布
    type_counts = {}
    for feat in result["features"]:
        lt = feat["properties"]["land_type"]
        type_counts[lt] = type_counts.get(lt, 0) + 1
    print("[统计]", " | ".join(f"{k}: {v}" for k, v in sorted(type_counts.items())))


if __name__ == "__main__":
    generate_land_segments()
