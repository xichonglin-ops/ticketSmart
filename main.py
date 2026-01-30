#!/usr/bin/env python3
"""
12306抢票软件主程序

功能：
- 自动抢票 北京 -> 陇西
- 支持车次: D29, Z151
- 支持日期: 2026-02-11, 2026-02-13
- 支持连座抢票（3人：2大人1小孩）

使用方法：
1. 运行程序
2. 输入12306账号密码
3. 输入乘客信息
4. 程序自动开始抢票
"""

import sys
import getpass
import signal
from datetime import datetime

from api import Train12306API
from grabber import ConsecutiveSeatGrabber
from config import PASSENGER_TYPES, ID_TYPES


def print_banner():
    """打印程序横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    12306 智能抢票系统                          ║
║                                                              ║
║  路线: 北京 -> 陇西                                           ║
║  车次: D29 / Z151                                            ║
║  日期: 2026-02-11 / 2026-02-13                               ║
║  票数: 3张 (2成人 + 1儿童)                                    ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def get_login_info() -> tuple:
    """获取登录信息"""
    print("\n" + "=" * 50)
    print("请输入12306登录信息")
    print("=" * 50)

    username = input("用户名(手机号/邮箱): ").strip()
    password = getpass.getpass("密码: ")

    return username, password


def get_passenger_info(index: int, passenger_type: str = "成人") -> dict:
    """
    获取单个乘客信息
    """
    print(f"\n--- 乘客 {index + 1} ({passenger_type}) ---")

    name = input("姓名: ").strip()

    print("证件类型:")
    print("  1. 二代身份证 (默认)")
    print("  2. 护照")
    print("  3. 港澳通行证")
    print("  4. 台湾通行证")
    id_type_choice = input("请选择 [1]: ").strip() or "1"

    id_type_map = {
        "1": "二代身份证",
        "2": "护照",
        "3": "港澳通行证",
        "4": "台湾通行证",
    }
    id_type = id_type_map.get(id_type_choice, "二代身份证")

    id_no = input(f"{id_type}号码: ").strip()
    mobile = input("手机号: ").strip()

    return {
        "name": name,
        "id_type": id_type,
        "id_no": id_no,
        "mobile": mobile,
        "type": passenger_type,
    }


def get_all_passengers() -> list:
    """获取所有乘客信息"""
    print("\n" + "=" * 50)
    print("请输入乘客信息 (共3人: 2成人 + 1儿童)")
    print("=" * 50)

    passengers = []

    # 2个成人
    for i in range(2):
        passenger = get_passenger_info(i, "成人")
        passengers.append(passenger)

    # 1个儿童
    passenger = get_passenger_info(2, "儿童")
    passengers.append(passenger)

    return passengers


def confirm_info(username: str, passengers: list) -> bool:
    """确认信息"""
    print("\n" + "=" * 50)
    print("请确认以下信息")
    print("=" * 50)

    print(f"\n登录账号: {username}")
    print(f"\n路线: 北京 -> 陇西")
    print(f"车次: D29 / Z151")
    print(f"日期: 2026-02-11 / 2026-02-13")

    print(f"\n乘客信息:")
    for i, p in enumerate(passengers):
        print(f"  {i + 1}. {p['name']} ({p['type']}) - {p['id_type']}: {p['id_no'][:4]}****{p['id_no'][-4:]}")

    print()
    confirm = input("确认无误? (Y/n): ").strip().lower()
    return confirm != "n"


def select_seat_types() -> list:
    """选择座位类型优先级"""
    print("\n" + "=" * 50)
    print("请选择座位类型优先级 (多选，用逗号分隔)")
    print("=" * 50)

    print("可选座位类型:")
    print("  1. 硬卧")
    print("  2. 软卧")
    print("  3. 硬座")
    print("  4. 二等座")
    print("  5. 一等座")
    print("  6. 无座")

    seat_map = {
        "1": "硬卧",
        "2": "软卧",
        "3": "硬座",
        "4": "二等座",
        "5": "一等座",
        "6": "无座",
    }

    default = "1,2,3"  # 默认: 硬卧 > 软卧 > 硬座
    choice = input(f"请选择 [{default}]: ").strip() or default

    selected = []
    for c in choice.split(","):
        c = c.strip()
        if c in seat_map:
            selected.append(seat_map[c])

    if not selected:
        selected = ["硬卧", "软卧", "硬座"]

    print(f"座位优先级: {' > '.join(selected)}")
    return selected


def select_login_method() -> str:
    """选择登录方式"""
    print("\n" + "=" * 50)
    print("请选择登录方式")
    print("=" * 50)

    print("  1. 账号密码登录")
    print("  2. 扫码登录")
    print("  3. Cookie登录 (推荐 - 从浏览器导入)")

    choice = input("请选择 [3]: ").strip() or "3"
    return choice


def main():
    """主程序入口"""
    print_banner()

    # 初始化API
    api = Train12306API()

    # 创建连座抢票器
    grabber = ConsecutiveSeatGrabber(api)

    # 设置默认配置
    grabber.set_route("北京", "陇西")
    grabber.set_dates(["2026-02-11", "2026-02-13"])
    grabber.set_trains(["D29", "Z151"])
    grabber.set_consecutive_count(3)

    # 处理Ctrl+C
    def signal_handler(sig, frame):
        print("\n\n收到中断信号，正在停止...")
        grabber.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # 选择登录方式
        login_method = select_login_method()

        if login_method == "1":
            # 账号密码登录
            username, password = get_login_info()
            print("\n正在登录...")
            if not api.login(username, password):
                print("登录失败，请检查账号密码")
                print("提示: 12306可能需要验证码或滑块验证，建议使用Cookie登录")
                return

        elif login_method == "2":
            # 扫码登录
            print("\n正在获取二维码...")
            if not api.login_with_qrcode():
                print("扫码登录失败")
                print("提示: 如果扫码持续失败，请尝试Cookie登录方式")
                return

        else:
            # Cookie登录
            from cookie_login import interactive_cookie_input, verify_login, export_cookies_guide

            print("\n" + "=" * 50)
            print("Cookie登录")
            print("=" * 50)

            # 先初始化session
            api.init_session()

            if not interactive_cookie_input(api.session):
                print("Cookie加载失败")
                export_cookies_guide()
                return

            # 验证登录状态
            print("\n正在验证登录状态...")
            is_logged_in, username = verify_login(api.session)
            if is_logged_in:
                api.is_login = True
                api.username = username
                print(f"Cookie登录成功! 用户: {username}")
            else:
                print("Cookie无效或已过期，请重新从浏览器导出")
                export_cookies_guide()
                return

        # 获取乘客信息
        passengers = get_all_passengers()

        # 确认信息
        if not confirm_info(api.username or "未知", passengers):
            print("已取消")
            return

        # 选择座位类型
        seat_types = select_seat_types()
        grabber.set_seat_types(seat_types)

        # 设置乘客
        grabber.set_passengers(passengers)

        # 开始抢票
        print("\n准备开始抢票...")
        print("提示: 按 Ctrl+C 可以随时停止")

        input("\n按回车键开始抢票...")

        grabber.start()

    except KeyboardInterrupt:
        print("\n\n用户中断")
        grabber.stop()
    except Exception as e:
        print(f"\n程序出错: {e}")
        import traceback
        traceback.print_exc()


def quick_test():
    """快速测试模式（不需要登录，仅查询）"""
    import sys
    print_banner()

    api = Train12306API()

    # 计算一个合理的测试日期（15天后，在预售期内）
    from datetime import datetime, timedelta
    test_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")

    print("\n" + "=" * 50)
    print("测试模式 - 验证API连接")
    print("=" * 50)
    sys.stdout.flush()

    # 先初始化session
    print("\n正在初始化连接...")
    sys.stdout.flush()
    if not api.init_session():
        print("初始化失败，请检查网络连接")
        return

    # 先用常见路线测试API是否正常
    print(f"\n[测试1] 查询热门路线 北京->上海 ({test_date})")
    sys.stdout.flush()

    trains = api.query_tickets(
        from_station="北京",
        to_station="上海",
        train_date=test_date
    )

    if trains:
        print(f"API正常! 找到 {len(trains)} 个车次")
        print("显示前3个车次:")
        for train in trains[:3]:
            print(f"  - {train['train_code']}: {train['start_time']}->{train['arrive_time']} 二等座:{train.get('ze', '--')}")
    else:
        print("未查到车次，可能是网络问题或12306接口变化")
        print("请检查网络连接后重试")
        return

    # 测试目标路线
    print(f"\n[测试2] 查询目标路线 北京->陇西 ({test_date})")
    trains = api.query_specific_trains(
        from_station="北京",
        to_station="陇西",
        train_date=test_date,
        train_codes=["D29", "Z151"]
    )

    if trains:
        print(f"找到 {len(trains)} 个目标车次:")
        for train in trains:
            print(f"\n车次: {train['train_code']}")
            print(f"  出发: {train['start_time']} 到达: {train['arrive_time']} 历时: {train['duration']}")
            print(f"  硬卧: {train.get('yw', '--')} | 软卧: {train.get('rw', '--')} | 硬座: {train.get('yz', '--')}")
    else:
        print("未找到D29/Z151车次")
        print("注意: 这两趟车可能不是每天都有，或者站点名称需要确认")

        # 查询所有北京到陇西的车次
        print(f"\n[测试3] 查询所有 北京->陇西 车次")
        all_trains = api.query_tickets("北京", "陇西", test_date)
        if all_trains:
            print(f"找到 {len(all_trains)} 个车次:")
            for train in all_trains[:5]:
                print(f"  - {train['train_code']}: {train['start_time']}->{train['arrive_time']}")
        else:
            print("该路线暂无直达车次，可能需要中转")

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        quick_test()
    else:
        main()
