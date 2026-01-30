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

方法1: 使用浏览器开发者工具（推荐）
-----------------------------------------
1. 在Chrome/Edge浏览器中打开 https://kyfw.12306.cn
2. 登录你的12306账号
3. 按 F12 打开开发者工具
4. 切换到 "Application"（应用程序）标签
5. 左侧选择 "Cookies" -> "https://kyfw.12306.cn"
6. 记录以下关键cookie的值:
   - JSESSIONID
   - tk
   - BIGipServerotn
   - BIGipServerpassport
   - route

方法2: 使用Console复制所有cookie
-----------------------------------------
1. 登录12306后，按F12打开开发者工具
2. 切换到 "Console"（控制台）标签
3. 输入以下命令并回车:
   document.cookie
4. 复制输出的cookie字符串

方法3: 使用浏览器插件
-----------------------------------------
1. 安装 "EditThisCookie" 或 "Cookie-Editor" 插件
2. 登录12306后，点击插件图标
3. 导出为JSON格式
4. 保存为 cookies.json 文件

将导出的cookie保存后，运行程序时选择"Cookie登录"即可。
"""
    print(guide)


def interactive_cookie_input(session) -> bool:
    """交互式输入cookie"""
    print("\n请选择cookie输入方式:")
    print("  1. 从cookies.json文件加载")
    print("  2. 手动输入cookie字符串")
    print("  3. 查看导出教程")

    choice = input("请选择 [1]: ").strip() or "1"

    if choice == "1":
        cookie_file = input("Cookie文件路径 [cookies.json]: ").strip() or "cookies.json"
        return load_cookies_from_file(session, cookie_file)

    elif choice == "2":
        print("请输入cookie字符串 (格式: name1=value1; name2=value2):")
        cookie_string = input().strip()
        if cookie_string:
            return load_cookies_from_string(session, cookie_string)
        return False

    elif choice == "3":
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
