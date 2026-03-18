"""Model provider and route service with tenant isolation."""

import base64
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import get_settings
from shared_errors import ErrorCode, NotFoundException
from shared_models import ModelProvider, ModelRoute

from app.utils.crypto import encrypt, mask_api_key


class ModelProviderService:
    """Operations for model providers and routes, scoped to a single tenant."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self._settings = get_settings()

    async def create_provider(self, data: dict) -> dict:
        """Create a model provider. Encrypt API key with AES-256."""
        api_key = data.pop("api_key")
        encrypted_bytes = encrypt(api_key, self._settings.encryption_key)
        encrypted_b64 = base64.b64encode(encrypted_bytes).decode("utf-8")

        provider = ModelProvider(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            provider_name=data["provider_name"],
            api_key_encrypted=encrypted_b64,
            base_url=data.get("base_url"),
            timeout_seconds=data.get("timeout_seconds", 60),
            max_context=data.get("max_context", 4096),
            status="active",
        )
        self.db.add(provider)
        await self.db.flush()

        return self._provider_to_dict(provider, api_key)

    def _provider_to_dict(self, provider: ModelProvider, original_api_key: str | None = None) -> dict:
        """Convert provider to dict with masked api_key."""
        masked = mask_api_key(original_api_key) if original_api_key else "****"
        return {
            "id": provider.id,
            "tenant_id": provider.tenant_id,
            "provider_name": provider.provider_name,
            "api_key_masked": masked,
            "base_url": provider.base_url,
            "timeout_seconds": provider.timeout_seconds,
            "max_context": provider.max_context,
            "status": provider.status,
            "created_at": provider.created_at,
        }

    async def list_providers(self) -> list[dict]:
        """List providers with masked API keys."""
        q = select(ModelProvider).where(
            ModelProvider.tenant_id == self.tenant_id,
        ).order_by(ModelProvider.created_at.desc())
        rows = (await self.db.execute(q)).scalars().all()
        return [self._provider_to_dict(p) for p in rows]

    async def test_provider(self, provider_id: uuid.UUID) -> dict:
        """Stub test for provider connectivity."""
        q = select(ModelProvider).where(
            ModelProvider.id == provider_id,
            ModelProvider.tenant_id == self.tenant_id,
        )
        result = await self.db.execute(q)
        provider = result.scalar_one_or_none()
        if provider is None:
            raise NotFoundException(
                error_code=ErrorCode.MODEL_PROVIDER_NOT_FOUND,
                message="模型供应商不存在",
            )
        return {"status": "ok"}

    async def create_route(self, data: dict) -> ModelRoute:
        """Create a model route."""
        route = ModelRoute(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            task_type=data["task_type"],
            provider_id=data["provider_id"],
            model_name=data["model_name"],
            priority=data.get("priority", 0),
            cost_limit_usd=data.get("cost_limit_usd"),
        )
        self.db.add(route)
        await self.db.flush()
        return route

    async def list_routes(self) -> list[ModelRoute]:
        """List model routes for the tenant."""
        q = select(ModelRoute).where(
            ModelRoute.tenant_id == self.tenant_id,
        ).order_by(ModelRoute.created_at.desc())
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows)

    async def update_route(self, route_id: uuid.UUID, data: dict) -> ModelRoute:
        """Update a model route."""
        q = select(ModelRoute).where(
            ModelRoute.id == route_id,
            ModelRoute.tenant_id == self.tenant_id,
        )
        result = await self.db.execute(q)
        route = result.scalar_one_or_none()
        if route is None:
            raise NotFoundException(
                error_code=ErrorCode.MODEL_ROUTE_NOT_FOUND,
                message="模型路由不存在",
            )
        for key, value in data.items():
            if value is not None:
                setattr(route, key, value)
        await self.db.flush()
        await self.db.refresh(route)
        return route

    async def delete_route(self, route_id: uuid.UUID) -> None:
        """Delete a model route."""
        q = select(ModelRoute).where(
            ModelRoute.id == route_id,
            ModelRoute.tenant_id == self.tenant_id,
        )
        result = await self.db.execute(q)
        route = result.scalar_one_or_none()
        if route is None:
            raise NotFoundException(
                error_code=ErrorCode.MODEL_ROUTE_NOT_FOUND,
                message="模型路由不存在",
            )
        await self.db.delete(route)
        await self.db.flush()
