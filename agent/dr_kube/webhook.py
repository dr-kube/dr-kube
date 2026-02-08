"""Alertmanager 웹훅 수신 서버"""
import os
import logging
from fastapi import FastAPI, BackgroundTasks, Request
from dotenv import load_dotenv

from dr_kube.converter import convert_alertmanager_payload
from dr_kube.graph import create_graph

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("dr-kube-webhook")

# 중복 방지용 세트
_processed_alerts: set[str] = set()

app = FastAPI(title="DR-Kube Webhook Server")


def process_issue(issue_data: dict, with_pr: bool = False):
    """이슈를 LangGraph 파이프라인으로 처리"""
    logger.info(f"처리 시작: {issue_data['id']} (type={issue_data['type']}, with_pr={with_pr})")
    try:
        graph = create_graph(with_pr=with_pr)
        result = graph.invoke({"issue_data": issue_data})

        if result.get("error"):
            logger.error(f"처리 실패: {issue_data['id']} - {result['error']}")
        else:
            logger.info(f"처리 완료: {issue_data['id']} - status={result.get('status')}")
            if result.get("pr_url"):
                logger.info(f"PR 생성됨: {result['pr_url']}")
    except Exception as e:
        logger.error(f"처리 중 예외: {issue_data['id']} - {e}")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook/alertmanager")
async def alertmanager_webhook(request: Request, background_tasks: BackgroundTasks):
    """Alertmanager 웹훅 수신"""
    payload = await request.json()

    issues = convert_alertmanager_payload(payload)
    total = len(payload.get("alerts", []))
    logger.info(f"알림 수신: {total}건, 처리 대상(firing): {len(issues)}건")

    with_pr = os.getenv("AUTO_PR", "false").lower() == "true"

    queued = []
    for issue in issues:
        alert_id = issue["id"]
        if alert_id in _processed_alerts:
            logger.info(f"중복 스킵: {alert_id}")
            continue
        _processed_alerts.add(alert_id)
        background_tasks.add_task(process_issue, issue, with_pr)
        queued.append(alert_id)

    return {
        "status": "accepted",
        "queued": len(queued),
        "alert_ids": queued,
    }


@app.post("/webhook/argocd")
async def argocd_webhook(request: Request, background_tasks: BackgroundTasks):
    """ArgoCD Notifications webhook (sync-failed, health-degraded). Body = single issue_data JSON."""
    body = await request.json()
    issue_id = body.get("id") or "argocd-unknown"
    logger.info(f"ArgoCD 이벤트 수신: {issue_id} (type={body.get('type', '')})")

    if issue_id in _processed_alerts:
        logger.info(f"중복 스킵: {issue_id}")
        return {"status": "accepted", "queued": 0, "reason": "duplicate"}

    _processed_alerts.add(issue_id)
    with_pr = os.getenv("AUTO_PR", "false").lower() == "true"
    background_tasks.add_task(process_issue, body, with_pr)
    return {"status": "accepted", "queued": 1, "id": issue_id}


def main():
    import uvicorn

    host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("WEBHOOK_PORT", "8080"))

    logger.info(f"DR-Kube 웹훅 서버 시작: http://{host}:{port}")
    logger.info(f"AUTO_PR={os.getenv('AUTO_PR', 'false')}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
