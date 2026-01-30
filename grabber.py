"""
抢票主逻辑模块
"""

import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from api import Train12306API
from config import TICKET_CONFIG, SEAT_TYPES


class TicketGrabber:
    """12306抢票器"""

    def __init__(self, api: Train12306API = None):
        self.api = api or Train12306API()
        self.is_running = False
        self.success = False

        # 抢票配置
        self.from_station = ""
        self.to_station = ""
        self.train_dates = []        # 可选日期列表
        self.train_codes = []        # 可选车次列表
        self.seat_types = []         # 座位类型优先级
        self.passengers = []         # 乘客列表
        self.ticket_count = 0        # 需要的票数
        self.start_time = None       # 抢票开始时间 (HH:MM格式)

    def set_route(self, from_station: str, to_station: str):
        """设置出发站和到达站"""
        self.from_station = from_station
        self.to_station = to_station
        print(f"路线已设置: {from_station} -> {to_station}")

    def set_dates(self, dates: List[str]):
        """设置出发日期列表"""
        self.train_dates = dates
        print(f"日期已设置: {', '.join(dates)}")

    def set_trains(self, train_codes: List[str]):
        """设置目标车次"""
        self.train_codes = train_codes
        print(f"车次已设置: {', '.join(train_codes)}")

    def set_seat_types(self, seat_types: List[str]):
        """设置座位类型优先级"""
        self.seat_types = seat_types
        print(f"座位类型已设置: {', '.join(seat_types)}")

    def set_passengers(self, passengers: List[Dict]):
        """
        设置乘客信息
        passengers: [
            {"name": "张三", "id_no": "xxx", "type": "成人", "mobile": "xxx"},
            {"name": "李四", "id_no": "xxx", "type": "儿童", "mobile": "xxx"},
        ]
        """
        self.passengers = passengers
        self.ticket_count = len(passengers)
        print(f"乘客已设置: {len(passengers)} 人")
        for p in passengers:
            print(f"  - {p['name']} ({p.get('type', '成人')})")

    def set_start_time(self, start_time: str):
        """
        设置抢票开始时间
        start_time: 24小时制时间字符串，如 "08:00", "06:30", "23:59"
        """
        if start_time:
            # 验证时间格式
            try:
                parts = start_time.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    self.start_time = f"{hour:02d}:{minute:02d}"
                    print(f"抢票开始时间已设置: {self.start_time}")
                else:
                    print("时间格式错误，将立即开始抢票")
                    self.start_time = None
            except (ValueError, IndexError):
                print("时间格式错误，将立即开始抢票")
                self.start_time = None
        else:
            self.start_time = None

    def _wait_for_start_time(self):
        """等待到指定的开始时间"""
        if not self.start_time:
            return

        target_hour, target_minute = map(int, self.start_time.split(":"))
        now = datetime.now()

        # 计算目标时间
        target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

        # 如果目标时间已过，设置为明天
        if target <= now:
            target = target + timedelta(days=1)
            print(f"目标时间已过，将在明天 {self.start_time} 开始抢票")

        # 计算等待时间
        wait_seconds = (target - now).total_seconds()

        if wait_seconds <= 0:
            return

        print("\n" + "=" * 50)
        print(f"⏰ 等待抢票开始时间: {self.start_time}")
        print(f"   当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   目标时间: {target.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   等待时长: {int(wait_seconds // 3600)}小时{int((wait_seconds % 3600) // 60)}分钟")
        print("=" * 50)
        print("\n提示: 按 Ctrl+C 可取消等待")

        # 倒计时等待
        try:
            while True:
                now = datetime.now()
                remaining = (target - now).total_seconds()

                if remaining <= 0:
                    print("\n\n⏰ 时间到! 开始抢票!")
                    # 提前一点点开始，确保不错过
                    break

                # 显示倒计时
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                seconds = int(remaining % 60)

                # 每秒更新一次显示
                print(f"\r⏳ 倒计时: {hours:02d}:{minutes:02d}:{seconds:02d}  ", end="", flush=True)

                # 最后10秒每0.1秒检查一次，其他时候每秒检查
                if remaining <= 10:
                    time.sleep(0.1)
                elif remaining <= 60:
                    time.sleep(0.5)
                else:
                    time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n已取消等待")
            raise

    def check_config(self) -> bool:
        """检查配置是否完整"""
        if not self.from_station or not self.to_station:
            print("错误: 请设置出发站和到达站")
            return False
        if not self.train_dates:
            print("错误: 请设置出发日期")
            return False
        if not self.train_codes:
            print("错误: 请设置目标车次")
            return False
        if not self.passengers:
            print("错误: 请设置乘客信息")
            return False
        if not self.seat_types:
            print("警告: 未设置座位类型，将尝试所有类型")
            self.seat_types = ["硬卧", "软卧", "二等座", "一等座", "硬座"]
        return True

    def check_tickets_available(self, train_info: Dict) -> Optional[str]:
        """
        检查车次是否有足够的票
        返回可用的座位类型，没有则返回None
        """
        # 座位字段映射
        seat_field_map = {
            "商务座": "swz",
            "一等座": "zy",
            "二等座": "ze",
            "高级软卧": "gr",
            "软卧": "rw",
            "动卧": "dw",
            "硬卧": "yw",
            "软座": "rz",
            "硬座": "yz",
            "无座": "wz",
        }

        for seat_type in self.seat_types:
            field = seat_field_map.get(seat_type)
            if not field:
                continue

            count = train_info.get(field, "--")
            if count == "--" or count == "" or count == "无":
                continue

            # 检查是否有足够的票
            if count == "有":
                return seat_type
            try:
                if int(count) >= self.ticket_count:
                    return seat_type
            except ValueError:
                continue

        return None

    def query_and_check(self) -> Optional[tuple]:
        """
        查询并检查是否有可用的票
        返回: (train_info, seat_type, date) 或 None
        """
        for date in self.train_dates:
            print(f"\n查询 {date} 的车票...")

            try:
                trains = self.api.query_specific_trains(
                    self.from_station,
                    self.to_station,
                    date,
                    self.train_codes
                )

                if not trains:
                    print(f"  未找到目标车次")
                    continue

                for train in trains:
                    train_code = train["train_code"]
                    can_buy = train.get("can_buy", "N")

                    if can_buy != "Y":
                        print(f"  {train_code}: 不可购买 ({train.get('remark', '')})")
                        continue

                    # 检查座位
                    available_seat = self.check_tickets_available(train)
                    if available_seat:
                        print(f"  {train_code}: 有票! 座位类型: {available_seat}")
                        return (train, available_seat, date)
                    else:
                        # 显示当前余票
                        self._print_train_tickets(train)

            except Exception as e:
                print(f"  查询出错: {e}")

        return None

    def _print_train_tickets(self, train: Dict):
        """打印车次余票信息"""
        code = train["train_code"]
        info_parts = []

        seat_fields = [
            ("二等座", "ze"), ("一等座", "zy"), ("商务座", "swz"),
            ("硬卧", "yw"), ("软卧", "rw"), ("硬座", "yz"), ("无座", "wz")
        ]

        for name, field in seat_fields:
            count = train.get(field, "--")
            if count and count != "--" and count != "":
                info_parts.append(f"{name}:{count}")

        if info_parts:
            print(f"  {code}: {', '.join(info_parts)}")
        else:
            print(f"  {code}: 暂无余票")

    def start(self, max_retry: int = None) -> bool:
        """
        开始抢票
        max_retry: 最大重试次数，None表示无限重试
        """
        if not self.check_config():
            return False

        if not self.api.is_login:
            print("错误: 请先登录12306")
            return False

        # 等待到指定的开始时间
        try:
            self._wait_for_start_time()
        except KeyboardInterrupt:
            print("用户取消")
            return False

        self.is_running = True
        self.success = False

        retry_count = 0
        max_retry = max_retry or TICKET_CONFIG["max_retry"]
        interval = TICKET_CONFIG["query_interval"]

        print("\n" + "=" * 50)
        print(f"🚄 开始抢票 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        print(f"路线: {self.from_station} -> {self.to_station}")
        print(f"日期: {', '.join(self.train_dates)}")
        print(f"车次: {', '.join(self.train_codes)}")
        print(f"乘客: {len(self.passengers)} 人")
        print(f"座位: {', '.join(self.seat_types)}")
        if self.start_time:
            print(f"定时: {self.start_time}")
        print("=" * 50)

        while self.is_running and retry_count < max_retry:
            retry_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{current_time}] 第 {retry_count} 次查询...")

            result = self.query_and_check()

            if result:
                train_info, seat_type, date = result

                print(f"\n发现可用车票！正在尝试抢票...")
                print(f"车次: {train_info['train_code']}")
                print(f"日期: {date}")
                print(f"座位: {seat_type}")

                # 尝试提交订单
                success = self.api.submit_order(
                    train_info=train_info,
                    passengers=self.passengers,
                    seat_type=seat_type,
                    train_date=date,
                    from_station=self.from_station,
                    to_station=self.to_station
                )

                if success:
                    self.success = True
                    self.is_running = False
                    print("\n" + "=" * 50)
                    print("抢票成功！请尽快前往12306完成支付！")
                    print("=" * 50)
                    return True
                else:
                    print("订单提交失败，继续尝试...")

            # 随机等待，避免被封
            wait_time = interval + random.uniform(0, 0.5)
            time.sleep(wait_time)

        print("\n抢票结束，未能成功购票")
        self.is_running = False
        return False

    def stop(self):
        """停止抢票"""
        self.is_running = False
        print("正在停止抢票...")


class ConsecutiveSeatGrabber(TicketGrabber):
    """
    连座抢票器
    尝试获取连续座位（注意：12306 API不直接支持连座查询，
    此功能通过选座功能尽量实现）
    """

    def __init__(self, api: Train12306API = None):
        super().__init__(api)
        self.need_consecutive = True
        self.consecutive_count = 3  # 需要连续的座位数

    def set_consecutive_count(self, count: int):
        """设置需要的连座数量"""
        self.consecutive_count = count
        print(f"连座数量已设置: {count} 人")

    def check_tickets_available(self, train_info: Dict) -> Optional[str]:
        """
        检查是否有足够的连座票
        由于12306不直接提供连座查询，我们检查余票数量是否充足
        """
        available_seat = super().check_tickets_available(train_info)

        if available_seat and self.need_consecutive:
            # 对于连座需求，我们需要确保票数充足
            # 实际连座需要在选座时处理
            seat_field_map = {
                "商务座": "swz", "一等座": "zy", "二等座": "ze",
                "高级软卧": "gr", "软卧": "rw", "动卧": "dw",
                "硬卧": "yw", "软座": "rz", "硬座": "yz", "无座": "wz",
            }

            field = seat_field_map.get(available_seat)
            count = train_info.get(field, "--")

            if count == "有":
                return available_seat

            try:
                # 为了连座，最好有更多余票
                if int(count) >= self.consecutive_count + 2:
                    return available_seat
                elif int(count) >= self.consecutive_count:
                    print(f"    注意: 余票紧张({count}张)，连座可能无法保证")
                    return available_seat
            except ValueError:
                pass

        return available_seat

    def generate_choose_seats(self, seat_type: str) -> str:
        """
        生成选座字符串
        尝试选择连续的座位
        """
        # 二等座/一等座选座: A/B/C/D/F 分别代表不同位置
        # 高铁二等座一排5个座位: A(窗) B C(过道) D(过道) F(窗)
        # 高铁一等座一排4个座位: A(窗) C(过道) D(过道) F(窗)

        if seat_type in ["二等座", "一等座"]:
            if self.consecutive_count == 3:
                # 选择连续的3个座位
                # 优先选择 A+B+C 或 C+D+F
                return "1A1B1C"  # 第一排ABC
            elif self.consecutive_count == 2:
                return "1A1B"
            else:
                return ""

        # 其他座位类型暂不支持选座
        return ""
