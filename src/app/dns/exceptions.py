from src.core.exceptions import NotFoundException


class DnsRecordNotFoundException(NotFoundException):
    detail = "DNS 레코드를 찾을 수 없습니다."

    def __init__(self, dns_id: str):
        super().__init__(detail=f"DNS 레코드를 찾을 수 없습니다: id={dns_id}")


class DeploymentForDnsNotFoundException(NotFoundException):
    detail = "DNS 연결 대상 Deployment를 찾을 수 없습니다."

    def __init__(self, deployment_id: str, namespace: str):
        super().__init__(detail=f"DNS 연결 대상 Deployment를 찾을 수 없습니다: {deployment_id} (namespace: {namespace})")
