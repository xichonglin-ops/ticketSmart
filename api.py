"""
12306 API 封装模块
"""

import re
import time
import json
import base64
import requests
from urllib.parse import urlencode
from datetime import datetime

from config import URLS, HEADERS, SEAT_TYPES, PASSENGER_TYPES, ID_TYPES
from stations import get_station_code, get_station_name


class Train12306API:
    """12306 API 客户端"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.is_login = False
        self.username = None
        self.token = None
        self.passengers = []
        self._initialized = False

    def init_session(self):
        """初始化session，获取必要的cookies"""
        if self._initialized:
            return True
        try:
            print("正在连接12306...")

            # 设置初始Referer
            self.session.headers["Referer"] = "https://www.12306.cn/"

            # 访问12306首页获取基础cookies
            resp = self.get("https://www.12306.cn/index/")
            print(f"  访问首页: {resp.status_code}")

            # 访问登录页面
            self.session.headers["Referer"] = "https://www.12306.cn/index/"
            resp = self.get("https://kyfw.12306.cn/otn/login/init")
            print(f"  访问登录页: {resp.status_code}")

            # 访问查票页面
            self.session.headers["Referer"] = "https://kyfw.12306.cn/otn/login/init"
            resp = self.get("https://kyfw.12306.cn/otn/leftTicket/init")
            print(f"  访问查票页: {resp.status_code}")

            if resp.status_code == 200:
                # 设置查票时的Referer
                self.session.headers["Referer"] = "https://kyfw.12306.cn/otn/leftTicket/init"
                self.session.headers["X-Requested-With"] = "XMLHttpRequest"
                print("连接成功!")
                self._initialized = True
                return True
            else:
                print(f"访问查票页面失败: {resp.status_code}")
                return False
        except Exception as e:
            print(f"初始化session失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """发送请求"""
        kwargs.setdefault("timeout", 30)
        try:
            response = self.session.request(method, url, **kwargs)
            return response
        except Exception as e:
            print(f"请求失败: {e}")
            raise

    def get(self, url: str, **kwargs) -> requests.Response:
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self._request("POST", url, **kwargs)

    def _safe_json(self, response) -> dict:
        """安全解析JSON响应"""
        try:
            return response.json()
        except Exception:
            return {}

    # ==================== 登录相关 ====================

    def get_captcha(self) -> tuple:
        """获取验证码图片 (base64, 图片数据)"""
        url = URLS["get_captcha"]
        params = {
            "login_site": "E",
            "module": "login",
            "rand": "sjrand",
            "_": int(time.time() * 1000)
        }
        response = self.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get("result_code") == "0":
                img_base64 = data.get("image", "")
                img_data = base64.b64decode(img_base64)
                return img_base64, img_data
        return None, None

    def check_captcha(self, answer: str) -> bool:
        """
        验证码校验
        answer: 点击位置坐标，如 "40,50,150,60"
        """
        url = URLS["check_captcha"]
        data = {
            "answer": answer,
            "rand": "sjrand",
            "login_site": "E"
        }
        response = self.post(url, data=data)
        if response.status_code == 200:
            result = response.json()
            return result.get("result_code") == "4"
        return False

    def login(self, username: str, password: str) -> bool:
        """
        登录12306
        注意: 现在12306主要使用扫码登录，密码登录可能需要滑块验证
        """
        # 先访问登录页面获取cookie
        self.get(URLS["login_init"])

        # 尝试登录
        login_url = URLS["login_check"]
        data = {
            "username": username,
            "password": password,
            "appid": "otn",
        }

        response = self.post(login_url, data=data)
        if response.status_code == 200:
            result = response.json()
            if result.get("result_code") == 0:
                # 获取认证token
                if self._get_auth_token():
                    self.is_login = True
                    self.username = username
                    print("登录成功!")
                    return True
            else:
                print(f"登录失败: {result.get('result_message', '未知错误')}")
        return False

    def _get_auth_token(self) -> bool:
        """获取认证token"""
        try:
            # 获取uamtk
            data = {"appid": "otn"}
            response = self.post(URLS["uamtk"], data=data)
            if response.status_code == 200:
                result = self._safe_json(response)
                if result.get("result_code") == 0:
                    tk = result.get("newapptk")
                    # 客户端认证
                    data = {"tk": tk}
                    response = self.post(URLS["uamauthclient"], data=data)
                    if response.status_code == 200:
                        result = self._safe_json(response)
                        if result.get("result_code") == 0:
                            self.token = result.get("apptk")
                            return True
        except Exception as e:
            print(f"获取认证token失败: {e}")
        return False

    def login_with_qrcode(self) -> bool:
        """
        扫码登录（推荐方式）
        返回二维码图片让用户扫描
        """
        # 先初始化session获取必要的cookies
        self.init_session()

        # 获取二维码
        qr_url = "https://kyfw.12306.cn/passport/web/create-qr64"
        data = {"appid": "otn"}

        try:
            response = self.post(qr_url, data=data)
        except Exception as e:
            print(f"获取二维码失败: {e}")
            return False

        if response.status_code != 200:
            print(f"获取二维码失败，状态码: {response.status_code}")
            return False

        result = self._safe_json(response)
        if result.get("result_code") != "0":
            print(f"获取二维码失败: {result.get('result_message', '未知错误')}")
            return False

        qr_base64 = result.get("image")
        uuid = result.get("uuid")

        if not qr_base64 or not uuid:
            print("二维码数据无效")
            return False

        # 保存二维码图片
        try:
            qr_data = base64.b64decode(qr_base64)
            with open("qrcode.png", "wb") as f:
                f.write(qr_data)
        except Exception as e:
            print(f"保存二维码失败: {e}")
            return False

        print("二维码已保存到 qrcode.png，请使用12306 APP扫描登录")
        print("提示: 打开12306 APP -> 我的 -> 右上角扫一扫")
        print("等待扫描...")

        # 轮询检查扫码状态
        check_url = "https://kyfw.12306.cn/passport/web/checkqr"
        for i in range(120):  # 最多等待2分钟
            time.sleep(1)
            try:
                response = self.post(check_url, data={"uuid": uuid, "appid": "otn"})
                if response.status_code != 200:
                    continue

                result = self._safe_json(response)
                code = result.get("result_code")

                if code == "0":
                    # 扫码确认成功
                    print(f"\n扫码确认成功!")
                    print(f"完整响应: {result}")

                    # 检查是否有uamtk
                    uamtk = result.get("uamtk")

                    # 调用uamtk接口获取认证token
                    if self._get_uamtk_after_qr(uamtk):
                        self.is_login = True
                        print("登录成功!")
                        return True
                    else:
                        print("登录验证失败，请重试")
                        return False
                elif code == "1":
                    # 等待扫描
                    if i % 10 == 0:
                        print(f"等待扫描中... ({i}/120秒)")
                    continue
                elif code == "2":
                    print("\r已扫描，请在手机上确认登录...", end="", flush=True)
                elif code == "3":
                    print("\n二维码已过期")
                    return False
                else:
                    msg = result.get("result_message", "")
                    if msg:
                        print(f"\n扫码状态: {msg}")
            except Exception as e:
                # 网络错误，继续重试
                continue

        print("\n扫码超时（2分钟），请重新运行程序")
        return False

    def _get_uamtk_after_qr(self, uamtk_from_qr: str = None) -> bool:
        """扫码成功后获取uamtk并完成认证"""
        try:
            newapptk = None

            # 如果扫码响应中有uamtk，直接使用
            if uamtk_from_qr:
                print(f"使用扫码响应中的uamtk")
                newapptk = uamtk_from_qr

            # 尝试多个可能的uamtk接口
            if not newapptk:
                uamtk_urls = [
                    "https://kyfw.12306.cn/passport/web/auth/uamtk",
                    "https://kyfw.12306.cn/otn/passport/web/auth/uamtk",
                    "https://kyfw.12306.cn/passport/web/auth/uamtk-static",
                ]

                print("正在获取认证token...")

                for uamtk_url in uamtk_urls:
                    print(f"尝试: {uamtk_url}")

                    # 设置正确的Referer
                    self.session.headers["Referer"] = "https://kyfw.12306.cn/otn/resources/login.html"

                    response = self.post(uamtk_url, data={"appid": "otn"})
                    print(f"  状态: {response.status_code}")
                    print(f"  原始响应: {response.text[:200]}")

                    if response.status_code != 200:
                        continue

                    # 检查是否是HTML
                    if "<html" in response.text[:100].lower():
                        print(f"  返回HTML页面，跳过")
                        continue

                    result = self._safe_json(response)
                    print(f"  解析结果: {result}")

                    if not result:
                        continue

                    result_code = result.get("result_code")
                    if result_code in [0, "0"]:
                        newapptk = result.get("newapptk")
                        if newapptk:
                            print(f"获取到token!")
                            break

            if not newapptk:
                print("无法获取认证token，尝试其他方法...")

                # 方法1: 访问登录回调页面
                print("尝试访问登录回调页面...")
                callback_urls = [
                    "https://kyfw.12306.cn/otn/login/userLogin",
                    "https://kyfw.12306.cn/otn/passport/web/login",
                    "https://kyfw.12306.cn/otn/view/index.html",
                ]
                for url in callback_urls:
                    self.session.headers["Referer"] = "https://kyfw.12306.cn/otn/resources/login.html"
                    response = self.get(url)
                    print(f"  {url}: {response.status_code}")

                # 方法2: 尝试直接访问用户中心看是否已登录
                return self._check_and_complete_login()

            # 第二步：调用uamauthclient完成认证
            print("正在完成认证...")
            self.session.headers["Referer"] = "https://kyfw.12306.cn/otn/passport/web/auth/uamtk"

            auth_data = {"tk": newapptk}
            response = self.post(URLS["uamauthclient"], data=auth_data)
            print(f"认证响应状态: {response.status_code}")

            if response.status_code != 200:
                print(f"认证失败: {response.status_code}")
                return False

            result = self._safe_json(response)
            print(f"认证响应: {result}")

            result_code = result.get("result_code")
            if result_code in [0, "0"]:
                self.token = result.get("apptk")
                self.username = result.get("username")
                print(f"认证成功! 用户: {self.username}")
                return True
            else:
                print(f"认证失败: {result.get('result_message', '未知错误')}")
                return False

        except Exception as e:
            print(f"认证过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _check_and_complete_login(self) -> bool:
        """检查是否已登录并完成认证"""
        try:
            # 打印当前cookies
            print(f"当前cookies: {list(self.session.cookies.keys())}")

            # 访问用户中心页面
            print("检查登录状态...")
            self.session.headers["Referer"] = "https://kyfw.12306.cn/otn/view/index.html"

            response = self.get("https://kyfw.12306.cn/otn/login/userLogin")
            print(f"用户页面状态: {response.status_code}")

            # 尝试多个用户信息接口
            user_apis = [
                ("https://kyfw.12306.cn/otn/modifyUser/initQueryUserInfoApi", {"_json_att": ""}),
                ("https://kyfw.12306.cn/otn/login/checkUser", {"_json_att": ""}),
                ("https://kyfw.12306.cn/otn/index/initMy12306Api", {"_json_att": ""}),
            ]

            for url, data in user_apis:
                print(f"尝试: {url}")
                response = self.post(url, data=data)
                print(f"  状态: {response.status_code}")
                print(f"  响应: {response.text[:300]}")

                if response.status_code == 200:
                    result = self._safe_json(response)

                    # checkUser接口
                    if "data" in result and "flag" in result.get("data", {}):
                        if result["data"]["flag"]:
                            print("checkUser: 已登录!")
                            self.username = "已登录用户"
                            return True

                    # initQueryUserInfoApi接口
                    if result.get("status") and result.get("data"):
                        user_info = result.get("data", {}).get("userDTO", {})
                        if user_info:
                            login_dto = user_info.get("loginUserDTO", {})
                            self.username = login_dto.get("user_name") or login_dto.get("name")
                            if self.username:
                                print(f"已登录用户: {self.username}")
                                return True

                    # initMy12306Api接口
                    if result.get("status") and result.get("data", {}).get("isLogin"):
                        self.username = result["data"].get("userName", "已登录用户")
                        print(f"已登录用户: {self.username}")
                        return True

            print("登录状态检查失败")
            return False
        except Exception as e:
            print(f"检查登录状态出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _complete_qr_login(self, uamtk: str) -> bool:
        """完成扫码登录（备用方法）"""
        # 客户端认证
        data = {"tk": uamtk}
        try:
            print(f"\n正在完成登录验证...")
            response = self.post(URLS["uamauthclient"], data=data)
            print(f"验证响应状态码: {response.status_code}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"验证响应: {result}")

                    if result.get("result_code") == 0:
                        self.token = result.get("apptk")
                        self.username = result.get("username")
                        return True
                    else:
                        print(f"认证失败: {result.get('result_message', '未知错误')}")
                except Exception as e:
                    print(f"解析响应失败: {e}")
                    print(f"响应内容: {response.text[:500]}")
            else:
                print(f"认证请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text[:500]}")
        except Exception as e:
            print(f"完成登录时出错: {e}")
        return False

    def check_login(self) -> bool:
        """检查登录状态"""
        response = self.post(URLS["uamtk"], data={"appid": "otn"})
        if response.status_code == 200:
            result = response.json()
            return result.get("result_code") == 0
        return False

    # ==================== 乘客信息 ====================

    def get_passengers(self) -> list:
        """获取常用联系人列表"""
        if not self.is_login:
            print("请先登录")
            return []

        response = self.post(URLS["get_passengers"], data={"_json_att": ""})
        if response.status_code == 200:
            result = response.json()
            if result.get("status"):
                data = result.get("data", {})
                self.passengers = data.get("normal_passengers", [])
                return self.passengers
        return []

    # ==================== 查询车票 ====================

    def query_tickets(self, from_station: str, to_station: str,
                      train_date: str, purpose_codes: str = "ADULT") -> list:
        """
        查询余票
        from_station: 出发站名称
        to_station: 到达站名称
        train_date: 出发日期 YYYY-MM-DD
        purpose_codes: ADULT-成人票 0X00-学生票
        """
        # 确保session已初始化
        self.init_session()

        try:
            from_code = get_station_code(from_station)
            to_code = get_station_code(to_station)
        except ValueError as e:
            print(f"车站查询失败: {e}")
            return []

        params = {
            "leftTicketDTO.train_date": train_date,
            "leftTicketDTO.from_station": from_code,
            "leftTicketDTO.to_station": to_code,
            "purpose_codes": purpose_codes,
        }

        # 12306查票接口URL可能会变化，尝试多个
        query_urls = [
            "https://kyfw.12306.cn/otn/leftTicket/queryE",
            "https://kyfw.12306.cn/otn/leftTicket/queryZ",
            "https://kyfw.12306.cn/otn/leftTicket/query",
            "https://kyfw.12306.cn/otn/leftTicket/queryA",
            "https://kyfw.12306.cn/otn/leftTicket/queryG",
            "https://kyfw.12306.cn/otn/leftTicket/queryT",
        ]

        trains = []
        last_error = None

        for base_url in query_urls:
            try:
                url = base_url + "?" + urlencode(params)
                response = self.get(url)

                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}"
                    continue

                # 检查是否是JSON响应
                content_type = response.headers.get("Content-Type", "")
                response_text = response.text[:500]

                # 如果是HTML页面，跳过
                if "<html" in response_text.lower() or "<!doctype" in response_text.lower():
                    last_error = "返回HTML页面"
                    continue

                result = self._safe_json(response)
                if not result:
                    last_error = f"无法解析JSON: {response_text[:100]}"
                    continue

                if result.get("status"):
                    data = result.get("data", {})
                    results = data.get("result", [])
                    station_map = data.get("map", {})

                    for item in results:
                        train_info = self._parse_train_info(item, station_map)
                        if train_info:
                            trains.append(train_info)

                    if trains:
                        return trains
                    else:
                        last_error = "查询成功但无车次数据"
                else:
                    # 可能需要登录或其他错误
                    messages = result.get("messages", [])
                    if messages:
                        last_error = f"API返回: {messages}"
                    else:
                        last_error = f"status=false: {str(result)[:100]}"

            except Exception as e:
                last_error = str(e)
                continue

        if last_error:
            print(f"调试信息: {last_error}")

        return trains

    def _parse_train_info(self, raw_data: str, station_map: dict) -> dict:
        """解析车次信息"""
        try:
            fields = raw_data.split("|")
            if len(fields) < 35:
                return None

            # 车次信息字段索引
            train_info = {
                "secret_str": fields[0],  # 用于订票的加密串
                "train_no": fields[2],     # 车次编号
                "train_code": fields[3],   # 车次名称 如 G1234
                "start_station_code": fields[4],
                "end_station_code": fields[5],
                "from_station_code": fields[6],
                "to_station_code": fields[7],
                "start_time": fields[8],   # 出发时间
                "arrive_time": fields[9],  # 到达时间
                "duration": fields[10],    # 历时
                "can_buy": fields[11],     # 是否可购买 Y/N
                "start_date": fields[13],  # 出发日期

                # 座位余票信息
                "swz": fields[32] or "--",   # 商务座
                "tz": fields[25] or "--",    # 特等座
                "zy": fields[31] or "--",    # 一等座
                "ze": fields[30] or "--",    # 二等座
                "gr": fields[21] or "--",    # 高级软卧
                "rw": fields[23] or "--",    # 软卧/一等卧
                "ydw": fields[33] or "--",   # 一等卧（动车）
                "edw": fields[22] or "--",   # 二等卧（动车）
                "dw": fields[27] or "--",    # 动卧
                "yw": fields[28] or "--",    # 硬卧
                "rz": fields[24] or "--",    # 软座
                "yz": fields[29] or "--",    # 硬座
                "wz": fields[26] or "--",    # 无座

                "remark": fields[1],         # 备注
            }

            # 转换车站代码为名称
            train_info["from_station"] = station_map.get(
                train_info["from_station_code"],
                train_info["from_station_code"]
            )
            train_info["to_station"] = station_map.get(
                train_info["to_station_code"],
                train_info["to_station_code"]
            )

            return train_info
        except Exception as e:
            print(f"解析失败: {e}")
            return None

    def query_specific_trains(self, from_station: str, to_station: str,
                              train_date: str, train_codes: list) -> list:
        """
        查询指定车次的余票
        train_codes: 车次列表，如 ["D29", "Z151"]
        """
        all_trains = self.query_tickets(from_station, to_station, train_date)
        target_trains = []

        for train in all_trains:
            if train["train_code"] in train_codes:
                target_trains.append(train)

        return target_trains

    # ==================== 订票相关 ====================

    def submit_order(self, train_info: dict, passengers: list,
                     seat_type: str, train_date: str,
                     from_station: str, to_station: str) -> bool:
        """
        提交订单请求
        train_info: 车次信息
        passengers: 乘客信息列表
        seat_type: 座位类型
        train_date: 出发日期
        """
        if not self.is_login:
            print("请先登录")
            return False

        secret_str = train_info.get("secret_str")
        if not secret_str:
            print("车次信息无效")
            return False

        # 提交订单前先验证登录状态（刷新session）
        check_resp = self.post("https://kyfw.12306.cn/otn/login/checkUser", data={"_json_att": ""})
        if check_resp.status_code == 200:
            check_result = self._safe_json(check_resp)
            if not check_result.get("data", {}).get("flag"):
                print("登录状态已过期，请重新登录")
                self.is_login = False
                return False

        # 提交订单请求
        data = {
            "secretStr": requests.utils.unquote(secret_str),
            "train_date": train_date,
            "back_train_date": train_date,
            "tour_flag": "dc",  # dc-单程 wc-往返
            "purpose_codes": "ADULT",
            "query_from_station_name": from_station,
            "query_to_station_name": to_station,
            "undefined": "",
        }

        response = self.post(URLS["submit_order"], data=data)
        if response.status_code != 200:
            print(f"提交订单请求失败: {response.status_code}")
            return False

        result = response.json()
        if not result.get("status"):
            print(f"提交订单失败: {result.get('messages', ['未知错误'])}")
            return False

        print("订单请求已提交，正在初始化...")

        # 初始化订单页面
        init_result = self._init_dc()
        if not init_result:
            return False

        token, ticket_info_for_passenger_form, order_request_dto = init_result

        # 检查订单信息（12306必需步骤）
        if not self._check_order_info(passengers, seat_type, token, ticket_info_for_passenger_form):
            print("订单信息检查失败")
            return False

        # 获取排队信息
        queue_count = self._get_queue_count(
            train_info, seat_type, train_date, token, ticket_info_for_passenger_form
        )
        print(f"当前排队人数: {queue_count}")

        # 确认订单
        return self._confirm_order(
            passengers, seat_type, token,
            ticket_info_for_passenger_form, order_request_dto
        )

    def _init_dc(self) -> tuple:
        """初始化订单确认页面，获取token等信息"""
        response = self.post(URLS["init_dc"], data={"_json_att": ""})
        if response.status_code != 200:
            print(f"初始化订单页面失败: HTTP {response.status_code}")
            return None

        html = response.text

        # 提取token
        token_match = re.search(r"var globalRepeatSubmitToken = '([^']+)'", html)
        ticket_match = re.search(r"var ticketInfoForPassengerForm=(\{.+?\});", html, re.S)
        order_match = re.search(r"var orderRequestDTO=(\{.+?\});", html, re.S)

        # 如果无法提取 token，检查是否是登录问题
        if not token_match or not ticket_match or not order_match:
            # 打印调试信息：HTML 长度和前500字符
            print(f"[调试] initDc 返回 HTML 长度: {len(html)}")
            print(f"[调试] HTML 内容预览: {html[:500]}...")

            # 检查是否返回了登录页面（明确的登录页面标识）
            if "用户未登录" in html or "请您先登录" in html:
                print("登录状态已失效，请重新登录")
                self.is_login = False
            elif len(html) < 1000:
                # 响应太短，可能是错误页面
                print(f"initDc 响应异常，内容: {html}")
            else:
                # 打印具体哪个字段缺失，便于调试
                missing = []
                if not token_match:
                    missing.append("globalRepeatSubmitToken")
                if not ticket_match:
                    missing.append("ticketInfoForPassengerForm")
                if not order_match:
                    missing.append("orderRequestDTO")
                print(f"无法获取订单token: {', '.join(missing)} 未找到")
            return None

        token = token_match.group(1)

        # 解析JSON（需要处理JS对象格式）
        try:
            ticket_info_str = ticket_match.group(1)
            # 简单处理：提取必要字段
            key_check_match = re.search(r"'key_check_isChange':'([^']+)'", ticket_info_str)
            train_location_match = re.search(r"'train_location':'([^']+)'", ticket_info_str)
            left_ticket_match = re.search(r"'leftTicketStr':'([^']*)'", ticket_info_str)

            ticket_info = {
                "key_check_isChange": key_check_match.group(1) if key_check_match else "",
                "train_location": train_location_match.group(1) if train_location_match else "",
                "leftTicketStr": left_ticket_match.group(1) if left_ticket_match else "",
            }

            order_str = order_match.group(1)
            train_date_match = re.search(r"'train_date':\{.+?'time':(\d+)", order_str)

            order_dto = {
                "train_date_time": train_date_match.group(1) if train_date_match else "",
            }

            return token, ticket_info, order_dto
        except Exception as e:
            print(f"解析订单页面失败: {e}")
            return None

    def _check_order_info(self, passengers: list, seat_type: str, token: str,
                          ticket_info: dict) -> bool:
        """
        检查订单信息 - 12306必需步骤
        在确认订单前必须调用此接口验证乘客信息
        """
        seat_code = SEAT_TYPES.get(seat_type, "1")

        passenger_str_list = []
        old_passenger_str_list = []

        for p in passengers:
            ptype = PASSENGER_TYPES.get(p.get("type", "成人"), "1")
            id_type = ID_TYPES.get(p.get("id_type", "二代身份证"), "1")

            new_str = f"{seat_code},0,{ptype},{p['name']},{id_type},{p['id_no']},{p.get('mobile', '')},N,{p.get('allEnc', '')}"
            passenger_str_list.append(new_str)

            old_str = f"{p['name']},{id_type},{p['id_no']},{ptype}_"
            old_passenger_str_list.append(old_str)

        data = {
            "cancel_flag": "2",
            "bed_level_order_num": "000000000000000000000000000000",
            "passengerTicketStr": "_".join(passenger_str_list),
            "oldPassengerStr": "".join(old_passenger_str_list),
            "tour_flag": "dc",
            "randCode": "",
            "whatsSelect": "1",
            "sessionId": "",
            "sig": "",
            "scene": "nc_login",
            "_json_att": "",
            "REPEAT_SUBMIT_TOKEN": token,
        }

        response = self.post(URLS["check_order_info"], data=data)
        if response.status_code == 200:
            result = response.json()
            if result.get("status"):
                data_info = result.get("data", {})
                if data_info.get("submitStatus"):
                    return True
                else:
                    err_msg = data_info.get("errMsg", "未知错误")
                    print(f"订单信息验证失败: {err_msg}")
                    # 检查是否需要验证码
                    if data_info.get("ifShowPassCode") == "Y":
                        print("需要验证码验证，暂不支持自动处理")
                    return False
            else:
                print(f"检查订单信息失败: {result.get('messages', ['未知错误'])}")
        else:
            print(f"检查订单信息请求失败: HTTP {response.status_code}")
        return False

    def _get_queue_count(self, train_info: dict, seat_type: str,
                         train_date: str, token: str, ticket_info: dict = None) -> int:
        """获取排队人数"""
        # 转换日期格式
        date_obj = datetime.strptime(train_date, "%Y-%m-%d")
        train_date_str = date_obj.strftime("%a %b %d %Y 00:00:00 GMT+0800 (中国标准时间)")

        # 使用从 initDc 获取的 leftTicketStr 和 train_location
        left_ticket = ticket_info.get("leftTicketStr", "") if ticket_info else ""
        train_location = ticket_info.get("train_location", "") if ticket_info else ""

        data = {
            "train_date": train_date_str,
            "train_no": train_info["train_no"],
            "stationTrainCode": train_info["train_code"],
            "seatType": SEAT_TYPES.get(seat_type, "1"),
            "fromStationTelecode": train_info["from_station_code"],
            "toStationTelecode": train_info["to_station_code"],
            "leftTicket": left_ticket,
            "purpose_codes": "00",
            "train_location": train_location,
            "REPEAT_SUBMIT_TOKEN": token,
            "_json_att": "",
        }

        response = self.post(URLS["get_queue_count"], data=data)
        if response.status_code == 200:
            result = response.json()
            if result.get("status"):
                data_info = result.get("data", {})
                count_str = data_info.get("count", "0")
                # 检查是否有票
                ticket_info_msg = data_info.get("ticket", "")
                if ticket_info_msg:
                    print(f"余票信息: {ticket_info_msg}")
                return int(count_str) if str(count_str).isdigit() else 0
        return 0

    def _confirm_order(self, passengers: list, seat_type: str, token: str,
                       ticket_info: dict, order_dto: dict) -> bool:
        """确认订单"""
        # 构建乘客信息字符串
        passenger_str_list = []
        old_passenger_str_list = []

        seat_code = SEAT_TYPES.get(seat_type, "1")

        for p in passengers:
            # 新格式乘客字符串
            # 座位类型,0,票类型,姓名,证件类型,证件号,手机号,N,乘客类型
            ptype = PASSENGER_TYPES.get(p.get("type", "成人"), "1")
            id_type = ID_TYPES.get(p.get("id_type", "二代身份证"), "1")

            new_str = f"{seat_code},0,{ptype},{p['name']},{id_type},{p['id_no']},{p.get('mobile', '')},N,{p.get('allEnc', '')}"
            passenger_str_list.append(new_str)

            # 旧格式乘客字符串
            old_str = f"{p['name']},{id_type},{p['id_no']},{ptype}_"
            old_passenger_str_list.append(old_str)

        passenger_ticket_str = "_".join(passenger_str_list)
        old_passenger_str = "".join(old_passenger_str_list)

        data = {
            "passengerTicketStr": passenger_ticket_str,
            "oldPassengerStr": old_passenger_str,
            "randCode": "",
            "purpose_codes": "00",
            "key_check_isChange": ticket_info.get("key_check_isChange", ""),
            "leftTicketStr": ticket_info.get("leftTicketStr", ""),
            "train_location": ticket_info.get("train_location", ""),
            "choose_seats": "",  # 选座
            "seatDetailType": "000",
            "whatsSelect": "1",
            "roomType": "00",
            "dwAll": "N",
            "_json_att": "",
            "REPEAT_SUBMIT_TOKEN": token,
        }

        response = self.post(URLS["confirm_single"], data=data)
        if response.status_code == 200:
            result = response.json()
            if result.get("status"):
                data_info = result.get("data", {})
                if data_info.get("submitStatus"):
                    print("订单提交成功，正在等待出票...")
                    return self._wait_for_order(token)
                else:
                    print(f"订单提交失败: {data_info.get('errMsg', '未知错误')}")
            else:
                print(f"确认订单失败: {result.get('messages', ['未知错误'])}")
        return False

    def _wait_for_order(self, token: str, max_wait: int = 60) -> bool:
        """等待订单结果"""
        for i in range(max_wait):
            time.sleep(1)

            params = {
                "random": str(int(time.time() * 1000)),
                "tourFlag": "dc",
                "REPEAT_SUBMIT_TOKEN": token,
            }

            response = self.get(URLS["query_order_wait"], params=params)
            if response.status_code == 200:
                result = response.json()
                if result.get("status"):
                    data = result.get("data", {})
                    order_id = data.get("orderId")
                    wait_time = data.get("waitTime", -1)
                    wait_count = data.get("waitCount", 0)

                    if order_id:
                        print(f"\n订票成功！订单号: {order_id}")
                        print("请尽快完成支付！")
                        return True
                    elif wait_time == -1:
                        # 订票失败
                        msg = data.get("msg", "未知原因")
                        print(f"\n订票失败: {msg}")
                        return False
                    elif wait_time >= 0:
                        print(f"\r等待中... 前面还有 {wait_count} 人，预计等待 {wait_time} 秒", end="")
                else:
                    messages = result.get("messages", [])
                    if messages:
                        print(f"\n查询失败: {messages}")
                        return False

        print("\n等待超时")
        return False

    def query_orders(self) -> list:
        """查询未完成订单"""
        if not self.is_login:
            return []

        data = {"_json_att": ""}
        response = self.post(URLS["query_no_complete"], data=data)

        if response.status_code == 200:
            result = response.json()
            if result.get("status"):
                data_info = result.get("data", {})
                return data_info.get("orderDBList", [])
        return []
