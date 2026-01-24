"""ResourceQuota 모델"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ResourceQuotaLimits:
    """ResourceQuota 하드 리밋 구성"""

    cpu: str
    memory: str
    disk: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "requests.cpu": self.cpu,
            "limits.cpu": self.cpu,
            "requests.memory": self.memory,
            "limits.memory": self.memory,
            "requests.storage": self.disk,
        }
