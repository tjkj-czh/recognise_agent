import os
import sys
import threading
import webbrowser
import time

# 兼容 PyInstaller 打包后的路径
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(BASE_DIR, 'compliance_agent'))

from web.app import create_app


def open_browser():
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000/')


if __name__ == '__main__':
    print("=" * 50)
    print("  用地识别智能体 - Web 预览版")
    print("  服务启动中，请稍候...")
    print("=" * 50)
    threading.Thread(target=open_browser, daemon=True).start()
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
