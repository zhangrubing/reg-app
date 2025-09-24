#!/usr/bin/env python3
"""修复后的API测试脚本"""
import requests
import json
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:8080"

def test_login():
    """测试登录获取token"""
    try:
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        response = requests.post(f"{BASE_URL}/api/login", json=login_data)
        print(f"登录请求: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"登录成功: {data}")
            # 从cookie中获取token
            if 'auth' in response.cookies:
                return response.cookies['auth']
            else:
                print("未找到auth cookie")
                return None
        else:
            print(f"登录失败: {response.text}")
            return None
    except Exception as e:
        print(f"登录异常: {e}")
        return None

def test_devices_api(token):
    """测试设备API"""
    print("\n=== 测试设备API ===")
    headers = {}
    cookies = {"auth": token} if token else {}
    
    # 获取设备列表
    response = requests.get(f"{BASE_URL}/api/devices", headers=headers, cookies=cookies)
    print(f"获取设备列表: {response.status_code}")
    if response.status_code == 200:
        print("✓ 设备列表获取成功")
        print(f"数据: {response.json()}")
    else:
        print(f"✗ 设备列表获取失败: {response.text}")
    
    # 获取设备统计
    response = requests.get(f"{BASE_URL}/api/devices/stats", headers=headers, cookies=cookies)
    print(f"获取设备统计: {response.status_code}")
    if response.status_code == 200:
        print("✓ 设备统计获取成功")
        print(f"数据: {response.json()}")
    else:
        print(f"✗ 设备统计获取失败: {response.text}")

def test_users_api(token):
    """测试用户API"""
    print("\n=== 测试用户API ===")
    headers = {}
    cookies = {"auth": token} if token else {}
    
    # 获取用户列表
    response = requests.get(f"{BASE_URL}/users", headers=headers, cookies=cookies)
    print(f"获取用户列表: {response.status_code}")
    if response.status_code == 200:
        print("✓ 用户列表获取成功")
        print(f"数据: {response.json()}")
    else:
        print(f"✗ 用户列表获取失败: {response.text}")
    
    # 获取用户统计
    response = requests.get(f"{BASE_URL}/users/statistics", headers=headers, cookies=cookies)
    print(f"获取用户统计: {response.status_code}")
    if response.status_code == 200:
        print("✓ 用户统计获取成功")
        print(f"数据: {response.json()}")
    else:
        print(f"✗ 用户统计获取失败: {response.text}")

def test_new_admin_apis(token):
    """测试新的管理员API"""
    print("\n=== 测试新的管理员API ===")
    headers = {}
    cookies = {"auth": token} if token else {}
    
    # 测试仪表板统计
    response = requests.get(f"{BASE_URL}/admin/dashboard/statistics", headers=headers, cookies=cookies)
    print(f"仪表板统计: {response.status_code}")
    if response.status_code == 200:
        print("✓ 仪表板统计成功")
        print(f"数据: {response.json()}")
    else:
        print(f"✗ 仪表板统计失败: {response.text}")
    
    # 测试激活统计
    response = requests.get(f"{BASE_URL}/admin/activations/statistics", headers=headers, cookies=cookies)
    print(f"激活统计: {response.status_code}")
    if response.status_code == 200:
        print("✓ 激活统计成功")
        print(f"数据: {response.json()}")
    else:
        print(f"✗ 激活统计失败: {response.text}")
    
    # 测试渠道列表
    response = requests.get(f"{BASE_URL}/admin/channels", headers=headers, cookies=cookies)
    print(f"渠道列表: {response.status_code}")
    if response.status_code == 200:
        print("✓ 渠道列表成功")
        print(f"数据: {response.json()}")
    else:
        print(f"✗ 渠道列表失败: {response.text}")
    
    # 测试审计统计
    response = requests.get(f"{BASE_URL}/admin/audit/statistics", headers=headers, cookies=cookies)
    print(f"审计统计: {response.status_code}")
    if response.status_code == 200:
        print("✓ 审计统计成功")
        print(f"数据: {response.json()}")
    else:
        print(f"✗ 审计统计失败: {response.text}")

def main():
    """主测试函数"""
    print("🚀 开始测试修复后的API...")
    print("=" * 50)
    
    # 首先测试登录
    print("📋 测试登录...")
    token = test_login()
    
    if token:
        print(f"\n🔐 获取到token: {token[:20]}...")
        
        # 测试修复后的API
        test_devices_api(token)
        test_users_api(token)
        test_new_admin_apis(token)
        
        print("\n🎉 API测试完成！")
    else:
        print("\n❌ 无法获取token，跳过其他测试")

if __name__ == "__main__":
    main()
