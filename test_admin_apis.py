#!/usr/bin/env python3
"""管理员API测试脚本"""
import requests
import json

# API基础URL
BASE_URL = "http://localhost:8083"

def test_admin_apis():
    """测试管理员API"""
    print("🚀 开始测试管理员API...")
    
    # 测试登录
    print("\n📋 测试登录...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    response = requests.post(f"{BASE_URL}/api/login", json=login_data)
    print(f"登录状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"登录成功: {data}")
        token = response.cookies.get('auth')
        print(f"获取token: {token[:20] if token else 'None'}")
    else:
        print(f"登录失败: {response.text}")
        return
    
    cookies = {'auth': token} if token else {}
    
    # 测试管理员仪表板统计
    print("\n📋 测试管理员仪表板统计...")
    response = requests.get(f"{BASE_URL}/admin/dashboard/statistics", cookies=cookies)
    print(f"仪表板统计状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"仪表板统计: {data}")
    else:
        print(f"仪表板统计失败: {response.text}")
    
    # 测试管理员激活统计
    print("\n📋 测试管理员激活统计...")
    response = requests.get(f"{BASE_URL}/admin/activations/statistics", cookies=cookies)
    print(f"激活统计状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"激活统计: {data}")
    else:
        print(f"激活统计失败: {response.text}")
    
    # 测试管理员渠道列表
    print("\n📋 测试管理员渠道列表...")
    response = requests.get(f"{BASE_URL}/admin/channels", cookies=cookies)
    print(f"渠道列表状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"渠道列表: {data}")
    else:
        print(f"渠道列表失败: {response.text}")
    
    # 测试管理员审计统计
    print("\n📋 测试管理员审计统计...")
    response = requests.get(f"{BASE_URL}/admin/audit/statistics", cookies=cookies)
    print(f"审计统计状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"审计统计: {data}")
    else:
        print(f"审计统计失败: {response.text}")
    
    # 测试管理员用户列表
    print("\n📋 测试管理员用户列表...")
    response = requests.get(f"{BASE_URL}/admin/users", cookies=cookies)
    print(f"管理员用户列表状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"管理员用户列表: {data}")
    else:
        print(f"管理员用户列表失败: {response.text}")
    
    # 测试管理员设备列表
    print("\n📋 测试管理员设备列表...")
    response = requests.get(f"{BASE_URL}/admin/devices", cookies=cookies)
    print(f"管理员设备列表状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"管理员设备列表: {data}")
    else:
        print(f"管理员设备列表失败: {response.text}")
    
    # 测试管理员许可证列表
    print("\n📋 测试管理员许可证列表...")
    response = requests.get(f"{BASE_URL}/admin/licenses", cookies=cookies)
    print(f"管理员许可证列表状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"管理员许可证列表: {data}")
    else:
        print(f"管理员许可证列表失败: {response.text}")
    
    # 测试管理员激活记录列表
    print("\n📋 测试管理员激活记录列表...")
    response = requests.get(f"{BASE_URL}/admin/activations", cookies=cookies)
    print(f"管理员激活记录列表状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"管理员激活记录列表: {data}")
    else:
        print(f"管理员激活记录列表失败: {response.text}")

if __name__ == "__main__":
    test_admin_apis()
