import os
import hmac
import hashlib
import json
import time
import base64
import requests
from flask import Flask, request, abort
from datetime import datetime

app = Flask(__name__)

GITHUB_SECRET = os.environ.get('GITHUB_SECRET')
FEISHU_WEBHOOK_URL = os.environ.get('FEISHU_WEBHOOK_URL')
FEISHU_SECRET = os.environ.get('FEISHU_SECRET')

# 检查必要的环境变量
if not FEISHU_WEBHOOK_URL:
    print("错误：未设置 FEISHU_WEBHOOK_URL 环境变量")
    print("请在 Vercel 项目设置中添加 FEISHU_WEBHOOK_URL 环境变量")

def verify_github_signature(req):
    """验证 GitHub Webhook 签名"""
    if not GITHUB_SECRET:
        return True
    
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        return False
    
    sha_name, signature_hex = signature.split('=', 1)
    if sha_name != 'sha256':
        return False
    
    mac = hmac.new(GITHUB_SECRET.encode('utf-8'), msg=request.data, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature_hex)

def gen_sign(timestamp, secret):
    """生成飞书签名"""
    string_to_sign = f'{timestamp}\n{secret}'
    hmac_code = hmac.new(string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return sign

def send_to_feishu(card_json):
    """发送消息到飞书"""
    if not FEISHU_WEBHOOK_URL:
        print("错误：FEISHU_WEBHOOK_URL 环境变量未设置，无法发送消息")
        return False
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "msg_type": "interactive",
        "card": card_json
    }
    
    if FEISHU_SECRET:
        timestamp = int(time.time())
        sign = gen_sign(timestamp, FEISHU_SECRET)
        payload["timestamp"] = timestamp
        payload["sign"] = sign
    
    try:
        response = requests.post(FEISHU_WEBHOOK_URL, headers=headers, json=payload)
        response.raise_for_status()
        print("消息已成功发送到飞书:", response.json())
        return True
    except requests.exceptions.RequestException as e:
        print(f"发送消息到飞书时出错: {e}")
        return False

def handle_push_event(payload):
    """处理 push 事件"""
    repo_name = payload['repository']['full_name']
    pusher_name = payload['pusher']['name']
    compare_url = payload['compare']
    branch = payload['ref'].replace('refs/heads/', '')
    
    commits_text = ""
    commit_count = len(payload['commits'])
    
    for commit in payload['commits'][:5]:
        commit_id = commit['id'][:7]
        message = commit['message'].split('\n')[0]
        author = commit['author']['name']
        commits_text += f"\\n- `{commit_id}`: {message} - {author}"
    
    if commit_count > 5:
        commits_text += f"\\n... 还有 {commit_count - 5} 个提交"
    
    if not commits_text:
        commits_text = "\\n没有新的提交"
    
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"content": f"🚀 [{repo_name}] 代码推送", "tag": "plain_text"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "content": f"**分支:** {branch}\\n**推送人:** {pusher_name}\\n**提交数量:** {commit_count}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "div",
                "text": {
                    "content": f"**提交详情:**{commits_text}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"content": "查看变更", "tag": "plain_text"},
                        "type": "primary",
                        "url": compare_url
                    },
                    {
                        "tag": "button",
                        "text": {"content": "访问仓库", "tag": "plain_text"},
                        "type": "default",
                        "url": payload['repository']['html_url']
                    }
                ]
            }
        ]
    }
    send_to_feishu(card)

def handle_issues_event(payload):
    """处理 issues 事件"""
    action = payload['action']
    issue = payload['issue']
    repo_name = payload['repository']['full_name']
    user = payload['sender']['login']
    
    action_map = {
        'opened': '创建',
        'closed': '关闭',
        'reopened': '重新打开',
        'assigned': '分配',
        'unassigned': '取消分配'
    }
    
    action_text = action_map.get(action, action)
    
    color_map = {
        'opened': 'green',
        'closed': 'red',
        'reopened': 'orange'
    }
    
    template_color = color_map.get(action, 'blue')
    
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": template_color,
            "title": {"content": f"🐛 [{repo_name}] Issue {action_text}", "tag": "plain_text"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "content": f"**标题:** {issue['title']}\\n**操作人:** {user}\\n**Issue #:** {issue['number']}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "div",
                "text": {
                    "content": f"**描述:** {(issue['body'] or '无描述')[:200]}{'...' if issue['body'] and len(issue['body']) > 200 else ''}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"content": "查看 Issue", "tag": "plain_text"},
                        "type": "primary",
                        "url": issue['html_url']
                    }
                ]
            }
        ]
    }
    send_to_feishu(card)

def handle_pull_request_event(payload):
    """处理 pull request 事件"""
    action = payload['action']
    pr = payload['pull_request']
    repo_name = payload['repository']['full_name']
    user = payload['sender']['login']
    
    action_map = {
        'opened': '创建',
        'closed': '关闭',
        'merged': '合并',
        'reopened': '重新打开',
        'review_requested': '请求审查'
    }
    
    action_text = action_map.get(action, action)
    
    color_map = {
        'opened': 'green',
        'closed': 'red',
        'merged': 'purple'
    }
    
    template_color = color_map.get(action, 'blue')
    
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": template_color,
            "title": {"content": f"🔀 [{repo_name}] Pull Request {action_text}", "tag": "plain_text"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "content": f"**标题:** {pr['title']}\\n**操作人:** {user}\\n**PR #:** {pr['number']}\\n**分支:** {pr['head']['ref']} → {pr['base']['ref']}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "div",
                "text": {
                    "content": f"**描述:** {(pr['body'] or '无描述')[:200]}{'...' if pr['body'] and len(pr['body']) > 200 else ''}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"content": "查看 PR", "tag": "plain_text"},
                        "type": "primary",
                        "url": pr['html_url']
                    }
                ]
            }
        ]
    }
    send_to_feishu(card)

def handle_release_event(payload):
    """处理 release 事件"""
    action = payload['action']
    release = payload['release']
    repo_name = payload['repository']['full_name']
    
    if action == 'published':
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "purple",
                "title": {"content": f"🎉 [{repo_name}] 新版本发布", "tag": "plain_text"}
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"**版本:** {release['tag_name']}\\n**名称:** {release['name']}\\n**发布人:** {release['author']['login']}",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "content": f"**发布说明:**\\n{(release['body'] or '无发布说明')[:300]}{'...' if release['body'] and len(release['body']) > 300 else ''}",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"content": "查看发布", "tag": "plain_text"},
                            "type": "primary",
                            "url": release['html_url']
                        }
                    ]
                }
            ]
        }
        send_to_feishu(card)

@app.route('/', methods=['GET'])
def health_check():
    """健康检查接口"""
    config_status = {
        'FEISHU_WEBHOOK_URL': '已配置' if FEISHU_WEBHOOK_URL else '未配置',
        'GITHUB_SECRET': '已配置' if GITHUB_SECRET else '未配置',
        'FEISHU_SECRET': '已配置' if FEISHU_SECRET else '未配置'
    }
    
    return {
        'status': 'ok' if FEISHU_WEBHOOK_URL else 'error',
        'message': 'GitHub-飞书机器人运行正常' if FEISHU_WEBHOOK_URL else '缺少必要的环境变量配置',
        'config': config_status,
        'timestamp': datetime.now().isoformat()
    }

@app.route('/', methods=['POST'])
def webhook_handler():
    """接收 Webhook 请求的入口"""
    # 检查环境变量
    if not FEISHU_WEBHOOK_URL:
        error_msg = "错误：FEISHU_WEBHOOK_URL 环境变量未配置"
        print(error_msg)
        return error_msg, 500
    
    # 验证签名
    if not verify_github_signature(request):
        abort(401, '无效签名')
    
    # 获取事件类型和数据
    event_type = request.headers.get('X-GitHub-Event')
    
    try:
        payload = request.get_json()
        if payload is None:
            error_msg = "错误：无法解析 JSON 数据"
            print(error_msg)
            return error_msg, 400
            
        print(f"收到 GitHub 事件: {event_type}")
        print(f"事件数据键: {list(payload.keys()) if payload else 'None'}")
        
        # 处理不同类型的事件
        if event_type == 'push':
            if 'repository' not in payload or 'pusher' not in payload:
                print("Push 事件数据不完整")
                return "Push 事件数据不完整", 400
            handle_push_event(payload)
        elif event_type == 'issues':
            if 'issue' not in payload or 'action' not in payload:
                print("Issues 事件数据不完整")
                return "Issues 事件数据不完整", 400
            handle_issues_event(payload)
        elif event_type == 'pull_request':
            if 'pull_request' not in payload or 'action' not in payload:
                print("Pull Request 事件数据不完整")
                return "Pull Request 事件数据不完整", 400
            handle_pull_request_event(payload)
        elif event_type == 'release':
            if 'release' not in payload or 'action' not in payload:
                print("Release 事件数据不完整")
                return "Release 事件数据不完整", 400
            handle_release_event(payload)
        elif event_type == 'ping':
            print("收到 GitHub Webhook ping 事件")
            return "Webhook 配置成功！", 200
        else:
            print(f"未处理的事件类型: {event_type}")
            return f"未处理的事件类型: {event_type}", 200
            
    except Exception as e:
        error_msg = f"处理事件时发生错误: {str(e)}"
        print(error_msg)
        print(f"错误详情: {type(e).__name__}")
        return error_msg, 500
    
    return 'OK', 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)
