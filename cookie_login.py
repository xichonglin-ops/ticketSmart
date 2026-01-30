"""
Cookie登录模块
用户可以从浏览器导出cookie后使用此功能登录
"""

import json
import os


def load_cookies_from_file(session, cookie_file: str = "cookies.json") -> bool:
    """
    从JSON文件加载cookies到session

    cookies.json格式:
    [
        {"name": "JSESSIONID", "value": "xxx", "domain": ".12306.cn"},
        {"name": "tk", "value": "xxx", "domain": ".12306.cn"},
        ...
    ]
    """
    if not os.path.exists(cookie_file):
        print(f"Cookie文件不存在: {cookie_file}")
        return False

    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        for cookie in cookies:
            session.cookies.set(
                cookie.get("name"),
                cookie.get("value"),
                domain=cookie.get("domain", ".12306.cn"),
                path=cookie.get("path", "/")
            )

        print(f"已加载 {len(cookies)} 个cookie")
        return True
    except Exception as e:
        print(f"加载cookie失败: {e}")
        return False


def load_cookies_from_string(session, cookie_string: str) -> bool:
    """
    从cookie字符串加载（浏览器开发者工具中复制的格式）

    格式: "name1=value1; name2=value2; ..."
    """
    try:
        cookies = cookie_string.strip().split(";")
        count = 0
        for cookie in cookies:
            cookie = cookie.strip()
            if "=" in cookie:
                name, value = cookie.split("=", 1)
                session.cookies.set(name.strip(), value.strip(), domain=".12306.cn")
                count += 1

        print(f"已加载 {count} 个cookie")
        return count > 0
    except Exception as e:
        print(f"解析cookie失败: {e}")
        return False


def export_cookies_guide():
    """打印如何从浏览器导出cookies的指南"""
    guide = """
╔══════════════════════════════════════════════════════════════╗
║                  如何导出浏览器Cookie                          ║
╚══════════════════════════════════════════════════════════════╝

⚠️  注意: document.cookie 无法获取 HttpOnly 的cookie!
    12306的关键cookie都是HttpOnly的，必须用下面的方法导出。

═══════════════════════════════════════════════════════════════
方法1: 从Network标签复制 (最可靠) ⭐推荐
═══════════════════════════════════════════════════════════════
1. 在Chrome/Edge浏览器中打开 https://kyfw.12306.cn 并登录
2. 按 F12 打开开发者工具
3. 切换到 "Network"（网络）标签
4. 在页面上随便点击一下（触发请求）
5. 在Network列表中点击任意一个请求
6. 在右侧找到 "Headers"（标头）-> "Request Headers"
7. 找到 "Cookie:" 行，复制整行cookie值
8. 运行程序，选择 "手动输入cookie字符串"，粘贴即可

═══════════════════════════════════════════════════════════════
方法2: 从Application标签手动复制
═══════════════════════════════════════════════════════════════
1. 登录12306后，按F12打开开发者工具
2. 切换到 "Application"（应用程序）标签
   (中文版可能是"应用"或"应用程序")
3. 左侧展开 "Cookies" -> 点击 "https://kyfw.12306.cn"
4. 右侧会显示所有cookie列表
5. 运行程序，选择 "逐个输入关键cookie"
6. 按提示输入各cookie的Value值

═══════════════════════════════════════════════════════════════
方法3: 使用浏览器插件 (最方便)
═══════════════════════════════════════════════════════════════
1. Chrome安装: "EditThisCookie" 或 "Cookie-Editor" 插件
2. 登录12306后，点击插件图标
3. 点击"导出"按钮，导出为JSON格式
4. 保存为 cookies.json 文件
5. 运行程序，选择 "从cookies.json文件加载"

关键Cookie说明:
- JSESSIONID: 会话ID (必需)
- tk: 登录令牌 (必需)
- uamtk: 认证令牌
- BIGipServerotn: 负载均衡
- BIGipServerpassport: 护照服务负载均衡
- route: 路由信息
"""
    print(guide)


def load_cookies_manually(session) -> bool:
    """手动逐个输入关键cookie"""
    print("\n请从浏览器Application标签中复制以下cookie的Value值:")
    print("(如果某个cookie不存在，直接按回车跳过)\n")

    key_cookies = [
        ("JSESSIONID", "会话ID - 必需"),
        ("tk", "登录令牌 - 必需"),
        ("uamtk", "认证令牌"),
        ("BIGipServerotn", "负载均衡"),
        ("BIGipServerpassport", "护照服务"),
        ("route", "路由信息"),
        ("_jc_save_fromStation", "出发站缓存"),
        ("_jc_save_toStation", "到达站缓存"),
    ]

    count = 0
    required_found = {"JSESSIONID": False, "tk": False}

    for name, desc in key_cookies:
        value = input(f"{name} ({desc}): ").strip()
        if value:
            session.cookies.set(name, value, domain=".12306.cn")
            count += 1
            if name in required_found:
                required_found[name] = True

    print(f"\n已加载 {count} 个cookie")

    if not required_found["JSESSIONID"] or not required_found["tk"]:
        print("⚠️  警告: 缺少必需的cookie (JSESSIONID 或 tk)")
        print("   登录可能会失败，建议使用Network标签复制完整cookie")

    return count > 0


def interactive_cookie_input(session) -> bool:
    """交互式输入cookie"""
    print("\n请选择cookie输入方式:")
    print("  1. 从cookies.json文件加载 (插件导出)")
    print("  2. 手动输入cookie字符串 (从Network标签复制) ⭐推荐")
    print("  3. 逐个输入关键cookie (从Application标签)")
    print("  4. 查看导出教程")

    choice = input("请选择 [2]: ").strip() or "2"

    if choice == "1":
        cookie_file = input("Cookie文件路径 [cookies.json]: ").strip() or "cookies.json"
        return load_cookies_from_file(session, cookie_file)

    elif choice == "2":
        print("\n" + "=" * 50)
        print("请从浏览器Network标签复制Cookie值:")
        print("=" * 50)
        print("步骤: F12 -> Network -> 点击任意请求 -> Headers -> Cookie")
        print("\n粘贴整行cookie (格式: name1=value1; name2=value2...):")
        cookie_string = input().strip()
        if cookie_string:
            return load_cookies_from_string(session, cookie_string)
        return False

    elif choice == "3":
        return load_cookies_manually(session)

    elif choice == "4":
        export_cookies_guide()
        return interactive_cookie_input(session)

    else:
        print("无效选择")
        return False


def verify_login(session) -> tuple:
    """验证cookie是否有效，返回(是否登录, 用户名)"""
    try:
        # 检查登录状态
        response = session.post(
            "https://kyfw.12306.cn/otn/login/checkUser",
            data={"_json_att": ""},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("data", {}).get("flag"):
                # 尝试获取用户名
                response = session.post(
                    "https://kyfw.12306.cn/otn/modifyUser/initQueryUserInfoApi",
                    data={"_json_att": ""},
                    timeout=10
                )
                if response.status_code == 200:
                    try:
                        result = response.json()
                        user_info = result.get("data", {}).get("userDTO", {})
                        login_dto = user_info.get("loginUserDTO", {})
                        username = login_dto.get("user_name") or login_dto.get("name") or "已登录用户"
                        return True, username
                    except:
                        pass
                return True, "已登录用户"

        return False, None
    except Exception as e:
        print(f"验证登录状态失败: {e}")
        return False, None
