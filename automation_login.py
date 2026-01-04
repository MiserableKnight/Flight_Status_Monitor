# -*- coding: utf-8 -*-
from DrissionPage import ChromiumPage, ChromiumOptions
import time
import configparser
import os

# ================= 配置文件读取 =================
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.ini')

def load_config():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"❌ 配置文件不存在: {CONFIG_FILE}")
    config.read(CONFIG_FILE, encoding='utf-8')
    try:
        return {
            'username': config.get('credentials', 'username'),
            'password': config.get('credentials', 'password'),
            'user_data_path': config.get('paths', 'user_data_path'),
            'target_url': config.get('target', 'url')
        }
    except Exception as e:
        raise ValueError(f"配置文件缺失: {e}")

try:
    cfg = load_config()
    USERNAME = cfg['username']
    PASSWORD = cfg['password']
    USER_DATA_PATH = cfg['user_data_path']
    TARGET_URL = cfg['target_url']
except Exception as e:
    print(f"❌ 初始化失败: {e}")
    exit(1)

def main():
    print("🚀 正在启动自动化程序...")

    co = ChromiumOptions()
    co.set_user_data_path(USER_DATA_PATH)
    co.set_local_port(9222)
    
    try:
        page = ChromiumPage(co)
        print("✅ 浏览器连接成功！")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return

    # --- 1. 初始跳转 ---
    # 这里加个判断，防止已经在中间页或者首页了还跳回登录页
    current_url = page.url
    if "index.html" not in current_url and "rbacUsersController" not in current_url and "login" not in current_url:
        print(f"🔗 跳转至登录页: {TARGET_URL}")
        page.get(TARGET_URL)
    elif "index.html" in current_url:
        print("✅ 检测到已在首页，直接刷新...")
        page.refresh()
    
    time.sleep(2)

    # --- 2. 登录处理 (如果还在登录页) ---
    if page.ele('#loginPwd'):
        print("🔒 开始登录流程...")
        try:
            # A. 填账号
            user_ele = page.ele('tag:input@@placeholder=请输入账号')
            if not user_ele: user_ele = page.ele('tag:input@@type=text')
            
            if user_ele:
                user_ele.clear()
                user_ele.input(USERNAME)
                # 点击空白处消除干扰
                try: page.ele('text:FLYWIN').click(by_js=True) 
                except: pass

            # B. 填密码
            pwd_ele = page.ele('#loginPwd')
            if pwd_ele:
                pwd_ele.clear()
                pwd_ele.input(PASSWORD)
                time.sleep(0.5)

                # C. 提交 (既然回车有效，我们直接用回车，不等按钮了)
                print("   ⚡ 发送【回车键】提交登录...")
                pwd_ele.input('\n') 
            
            else:
                print("❌ 找不到密码框")
                return

        except Exception as e:
            print(f"❌ 登录操作出错: {e}")
    else:
        print("ℹ️ 未检测到登录框，可能已登录或在中间页，继续检查...")

    # --- 3. 智能等待：监控登录跳转与中间页 (核心修改) ---
    print("\n⏳ 正在等待系统响应 (最长等待 60秒)...")
    
    # 我们设置一个 60 秒的循环，每秒看一眼浏览器变成啥样了
    max_wait = 60
    found_target = False
    
    for i in range(max_wait):
        # 情况 A: 出现了中间页的 "WEB" 按钮
        # 识别特征：文本是 WEB 的链接，或者 tag:a 且 text=WEB
        web_btn = page.ele('text:WEB') # 简单粗暴找WEB字样
        
        if web_btn and web_btn.states.is_displayed:
            print(f"   👀 第 {i+1}秒: 检测到中间页 'WEB' 按钮！")
            print("   👉 正在点击 'WEB' 进入系统...")
            web_btn.click(by_js=True) # 强制点击
            time.sleep(1) # 给它一点反应时间
            # 点击后，继续循环等待直到进入 index.html
            continue 

        # 情况 B: 已经成功到达首页 (index.html)
        if "mainController/index.html" in page.url:
            print(f"   ✅ 第 {i+1}秒: 成功抵达首页！")
            found_target = True
            break
        
        # 情况 C: 还在登录页 (可能卡住了)
        if page.ele('#loginPwd') and i > 10:
            # 如果等了10秒还在输入密码的地方，可能真没点上，补一刀
            print("   ⚠️ 似乎还停留在登录页，尝试补按一次回车...")
            page.ele('#loginPwd').input('\n')
        
        # 还没刷出来，打印个点，等1秒
        print(".", end="", flush=True)
        time.sleep(1)

    print("\n") # 换行

    # --- 4. 最终验证 ---
    if found_target or "index.html" in page.url:
        print(f"🎉 任务成功！当前页面标题: {page.title}")
        print("🚀 现在可以执行后续的数据抓取逻辑了...")
    else:
        print("❌ 等待超时！")
        print("请检查：1. 密码对不对？ 2. 系统是不是崩了？ 3. 需要手动辅助一下？")

    print("👋 脚本就绪。")

if __name__ == "__main__":
    main()