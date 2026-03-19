"""Slack 코파일럿 통합 - Block Kit 제안 메시지 + 인터랙티브 액션

환경변수:
  SLACK_BOT_TOKEN   : xoxb- 로 시작하는 Bot OAuth 토큰 (필수)
  SLACK_CHANNEL     : 제안 메시지를 보낼 채널 (기본: #dr-kube)
  SLACK_SIGNING_SECRET : 요청 서명 검증용 (선택, 보안 강화)
"""
import os
import logging

logger = logging.getLogger("dr-kube-slack")

_SEVERITY_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
_FIX_METHOD_LABEL = {"rule_based": "룰 기반", "llm": "LLM", "none": "분석만"}


def _client():
    from slack_sdk import WebClient
    token = os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN 환경변수가 설정되지 않았습니다")
    return WebClient(token=token)


def is_configured() -> bool:
    """Slack Bot Token이 설정됐는지 확인"""
    return bool(os.getenv("SLACK_BOT_TOKEN", ""))


def send_proposal(result: dict, action_id: str, thread_ts: str = "") -> tuple[bool, str, str]:
    """분석 결과를 Slack에 코파일럿 제안 메시지로 전송.

    버튼:
      ✅ PR 생성  - 분석안 그대로 PR 생성
      ✏️ 수정 요청 - 모달 입력 → LLM 재생성
      ❌ 무시      - 이슈 무시

    thread_ts: 설정 시 해당 메시지의 스레드 답글로 전송 (수정 요청 재분석용)

    Returns:
        (success, channel, message_ts)
    """
    channel = os.getenv("SLACK_CHANNEL", "dr-kube").lstrip("#")
    issue = result.get("issue_data", {})
    severity = result.get("severity", "medium")
    root_cause = result.get("root_cause", "N/A")
    fix_description = result.get("fix_description", "")
    target_file = result.get("target_file", "")
    fix_method = result.get("fix_method", "")

    severity_icon = _SEVERITY_EMOJI.get(severity.lower(), "⚪")
    method_label = _FIX_METHOD_LABEL.get(fix_method, "")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🔍 DR-Kube 이슈 감지 — 검토 요청"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*타입:*\n`{issue.get('type', 'unknown')}`"},
                {"type": "mrkdwn", "text": f"*리소스:*\n`{issue.get('resource', 'unknown')}`"},
                {"type": "mrkdwn", "text": f"*네임스페이스:*\n`{issue.get('namespace', 'default')}`"},
                {"type": "mrkdwn", "text": f"*심각도:*\n{severity_icon} {severity.upper()}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*🔍 근본 원인*\n{root_cause}"},
        },
    ]

    # 수정 제안이 있을 때만 표시
    if fix_description and target_file:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*🔧 제안 수정 ({method_label})*\n"
                    f"파일: `{target_file}`\n"
                    f"```{fix_description}```"
                ),
            },
        })

    blocks += [
        {"type": "divider"},
        {
            "type": "actions",
            "block_id": f"proposal_{action_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ PR 생성"},
                    "style": "primary",
                    "action_id": "approve",
                    "value": action_id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✏️ 수정 요청"},
                    "action_id": "request_modify",
                    "value": action_id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ 무시"},
                    "style": "danger",
                    "action_id": "reject",
                    "value": action_id,
                },
            ],
        },
    ]

    try:
        kwargs: dict = dict(
            channel=channel,
            blocks=blocks,
            text=f"DR-Kube: {issue.get('type')} 이슈 감지 ({issue.get('resource')})",
        )
        if thread_ts:
            kwargs["thread_ts"] = thread_ts
        resp = _client().chat_postMessage(**kwargs)
        logger.info(f"Slack 제안 전송 완료: action_id={action_id} ts={resp['ts']}")
        return True, resp["channel"], resp["ts"]
    except Exception as e:
        logger.error(f"Slack 제안 전송 실패: {e}")
        return False, "", ""


def update_proposal(channel: str, ts: str, status: str, detail: str = "") -> None:
    """제안 메시지를 처리 결과로 업데이트 (버튼 제거).

    status: approved | rejected | pr_created | modified | error
    """
    text_map = {
        "approved": f"✅ *PR 생성 시작됨*\n{detail}",
        "rejected": "❌ *무시됨*",
        "pr_created": f"✅ *PR 생성 완료*\n{detail}",
        "merged": f"⚡ *머지됨, ArgoCD 동기화 중...*\nPR {detail}",
        "modified": f"✏️ *수정 요청 처리 중...*\n{detail}",
        "error": f"⚠️ *오류 발생*\n{detail}",
    }
    text = text_map.get(status, status)

    try:
        _client().chat_update(
            channel=channel,
            ts=ts,
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": text}}],
            text=text,
        )
    except Exception as e:
        logger.error(f"Slack 메시지 업데이트 실패: {e}")


def send_pr_ready(
    result: dict,
    pr_url: str,
    pr_number: int,
    channel: str,
    ts: str,
) -> str:
    """PR 생성 완료를 원본 메시지 스레드에 답글로 전송.

    1. 원본 메시지 버튼 제거 (처리 완료 표시)
    2. 스레드 답글: PR URL + [⚡ 머지] [🔗 PR 보기] 버튼

    Returns: 새 스레드 메시지 ts (merge 버튼 업데이트에 사용)
    """
    issue = result.get("issue_data", {})
    severity = result.get("severity", "medium")
    root_cause = result.get("root_cause", "N/A")
    fix_description = result.get("fix_description", "")
    fix_method = result.get("fix_method", "")
    target_file = result.get("target_file", "")

    severity_icon = _SEVERITY_EMOJI.get(severity.lower(), "⚪")
    method_label = _FIX_METHOD_LABEL.get(fix_method, "")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "✅ PR 생성 완료 — 검토 후 머지해주세요"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*타입:*\n`{issue.get('type', 'unknown')}`"},
                {"type": "mrkdwn", "text": f"*리소스:*\n`{issue.get('resource', 'unknown')}`"},
                {"type": "mrkdwn", "text": f"*심각도:*\n{severity_icon} {severity.upper()}"},
                {"type": "mrkdwn", "text": f"*PR:*\n<{pr_url}|#{pr_number}>"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*🔍 근본 원인*\n{root_cause}"},
        },
    ]

    if fix_description and target_file:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*🔧 수정 내용 ({method_label})*\n"
                    f"파일: `{target_file}`\n"
                    f"```{fix_description}```"
                ),
            },
        })

    blocks += [
        {"type": "divider"},
        {
            "type": "actions",
            "block_id": f"pr_ready_{pr_number}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "⚡ 머지"},
                    "style": "primary",
                    "action_id": "merge_pr",
                    "value": str(pr_number),
                    "confirm": {
                        "title": {"type": "plain_text", "text": "PR 머지 확인"},
                        "text": {"type": "mrkdwn", "text": f"PR <{pr_url}|#{pr_number}>를 squash merge 하시겠습니까?"},
                        "confirm": {"type": "plain_text", "text": "머지"},
                        "deny": {"type": "plain_text", "text": "취소"},
                    },
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🔗 PR 보기"},
                    "url": pr_url,
                    "action_id": "view_pr",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✏️ 수정 요청"},
                    "action_id": "request_modify_pr",
                    "value": str(pr_number),
                },
            ],
        },
    ]

    try:
        client = _client()
        # 1. 원본 이슈 감지 메시지에서 버튼만 제거 (내용 유지)
        client.chat_update(
            channel=channel,
            ts=ts,
            blocks=[
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "🔍 DR-Kube 이슈 감지 — PR 생성 진행 중"},
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*타입:*\n`{issue.get('type', 'unknown')}`"},
                        {"type": "mrkdwn", "text": f"*리소스:*\n`{issue.get('resource', 'unknown')}`"},
                        {"type": "mrkdwn", "text": f"*심각도:*\n{severity_icon} {severity.upper()}"},
                        {"type": "mrkdwn", "text": f"*PR:*\n<{pr_url}|#{pr_number}>"},
                    ],
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*🔍 근본 원인*\n{root_cause}"},
                },
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": "✅ PR 생성 완료 — 아래 스레드에서 머지 진행"}],
                },
            ],
            text="DR-Kube: PR 생성 완료",
        )
        # 2. 스레드 답글로 PR 완료 + 머지 버튼
        resp = client.chat_postMessage(
            channel=channel,
            thread_ts=ts,
            blocks=blocks,
            text=f"DR-Kube: PR #{pr_number} 생성 완료 — 머지 대기 중",
        )
        logger.info(f"PR 완료 스레드 답글: pr_number={pr_number} ts={resp['ts']}")
        return resp["ts"]
    except Exception as e:
        logger.error(f"PR 완료 메시지 전송 실패: {e}")
        return ""


def send_recovery_complete(
    channel: str,
    ts: str,
    issue_data: dict,
    fix_description: str,
    pr_url: str,
    pr_number: int,
) -> None:
    """ArgoCD sync 완료 후 복구 완료 메시지로 최종 업데이트."""
    issue_type = issue_data.get("type", "unknown")
    resource = issue_data.get("resource", "unknown")
    namespace = issue_data.get("namespace", "default")

    text = (
        f"✅ *DR-Kube 복구 완료*\n\n"
        f"📌 이슈: `{resource}` {issue_type}\n"
        f"🌐 네임스페이스: `{namespace}`\n"
        f"🔧 변경: {fix_description}\n"
        f"🔗 PR: <{pr_url}|#{pr_number}>\n"
        f"📊 상태: ArgoCD Synced & Healthy ✅"
    )

    try:
        _client().chat_postMessage(
            channel=channel,
            thread_ts=ts,
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": text}}],
            text=text,
        )
        logger.info(f"복구 완료 스레드 답글: resource={resource} pr={pr_number}")
    except Exception as e:
        logger.error(f"복구 완료 메시지 전송 실패: {e}")


def open_modify_modal(trigger_id: str, action_id: str) -> bool:
    """수정 요청 모달 열기.

    사용자가 자유 텍스트로 수정 지시를 입력 →
    modal callback_id=modify_modal_{action_id} 로 webhook에서 수신
    """
    try:
        _client().views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": f"modify_modal_{action_id}",
                "title": {"type": "plain_text", "text": "수정 요청"},
                "submit": {"type": "plain_text", "text": "전송"},
                "close": {"type": "plain_text", "text": "취소"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "modify_comment",
                        "label": {"type": "plain_text", "text": "수정 요청 내용"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "comment",
                            "multiline": True,
                            "placeholder": {
                                "type": "plain_text",
                                "text": "예: memory limit을 512Mi로 올려주세요. PDB도 추가해주세요.",
                            },
                        },
                    }
                ],
                "private_metadata": action_id,
            },
        )
        return True
    except Exception as e:
        logger.error(f"Slack 모달 열기 실패: {e}")
        return False
