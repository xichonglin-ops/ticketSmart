"""
车站代码管理模块
"""

import re
import requests
from config import URLS, HEADERS

# 常用车站代码缓存
STATION_CODES = {
    # 北京相关
    "北京": "BJP",
    "北京北": "VAP",
    "北京东": "BOP",
    "北京南": "VNP",
    "北京西": "BXP",
    "北京朝阳": "IFP",

    # 陇西
    "陇西": "LXJ",

    # 兰州相关
    "兰州": "LZJ",
    "兰州西": "LXJ",

    # 其他常用
    "上海": "SHH",
    "上海虹桥": "AOH",
    "广州": "GZQ",
    "深圳": "SZQ",
    "天津": "TJP",
    "西安": "XAY",
    "成都": "CDW",
    "重庆": "CQW",
}


class StationManager:
    """车站信息管理"""

    def __init__(self):
        self.stations = STATION_CODES.copy()
        self._loaded = False

    def load_stations_online(self):
        """从12306在线获取完整车站列表"""
        try:
            response = requests.get(URLS["station_name"], headers=HEADERS, timeout=10)
            if response.status_code == 200:
                # 解析车站数据: @bjb|北京北|VAP|beijingbei|bjb|0
                pattern = r"@([a-z]+)\|([^\|]+)\|([A-Z]+)\|"
                matches = re.findall(pattern, response.text)
                for _, name, code in matches:
                    self.stations[name] = code
                self._loaded = True
                print(f"成功加载 {len(self.stations)} 个车站信息")
                return True
        except Exception as e:
            print(f"加载车站信息失败: {e}")
        return False

    def get_station_code(self, station_name: str) -> str:
        """获取车站代码"""
        if station_name in self.stations:
            return self.stations[station_name]

        # 如果本地没有，尝试在线加载
        if not self._loaded:
            self.load_stations_online()
            if station_name in self.stations:
                return self.stations[station_name]

        raise ValueError(f"未找到车站: {station_name}")

    def get_station_name(self, station_code: str) -> str:
        """根据代码获取车站名称"""
        for name, code in self.stations.items():
            if code == station_code:
                return name
        return station_code

    def search_station(self, keyword: str) -> list:
        """搜索车站"""
        results = []
        for name, code in self.stations.items():
            if keyword in name:
                results.append((name, code))
        return results


# 全局实例
station_manager = StationManager()


def get_station_code(name: str) -> str:
    """获取车站代码的便捷函数"""
    return station_manager.get_station_code(name)


def get_station_name(code: str) -> str:
    """获取车站名称的便捷函数"""
    return station_manager.get_station_name(code)
