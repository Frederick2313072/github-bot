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
    except requests.exceptions.RequestException as e:
        print(f"发送消息到飞书时出错: {e}")

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
                    "content": f"**描述:** {issue['body'][:200]}{'...' if len(issue['body']) > 200 else ''}",
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
                    "content": f"**描述:** {pr['body'][:200] if pr['body'] else '无描述'}{'...' if pr['body'] and len(pr['body']) > 200 else ''}",
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
                        "content": f"**发布说明:**\\n{release['body'][:300] if release['body'] else '无发布说明'}{'...' if release['body'] and len(release['body']) > 300 else ''}",
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
    return {
        'status': 'ok',
        'message': 'GitHub-飞书机器人运行正常',
        'timestamp': datetime.now().isoformat()
    }

@app.route('/', methods=['POST'])
def webhook_handler():
    """接收 Webhook 请求的入口"""
    if not verify_github_signature(request):
        abort(401, '无效签名')
    
    event_type = request.headers.get('X-GitHub-Event')
    payload = request.json
    
    print(f"收到 GitHub 事件: {event_type}")
    
    try:
        if event_type == 'push':
            handle_push_event(payload)
        elif event_type == 'issues':
            handle_issues_event(payload)
        elif event_type == 'pull_request':
            handle_pull_request_event(payload)
        elif event_type == 'release':
            handle_release_event(payload)
        else:
            print(f"未处理的事件类型: {event_type}")
    except Exception as e:
        print(f"处理事件时发生错误: {e}")
        return f'处理事件时发生错误: {str(e)}', 500
    
    return 'OK', 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)
