from abc import ABC, abstractmethod

from src.core.kubernetes.uow import UoW


class BaseUseCase(ABC):
    @abstractmethod
    async def __call__(
            self,
            *args,
            **kwargs
    ):
        raise NotImplementedError