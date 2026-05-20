from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    campaigns,
    comments,
    commerce,
    content,
    conversations,
    dashboard,
    funnels,
    knowledge,
    leads,
    logs,
    me,
    meta,
    settings,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(meta.router)
api_router.include_router(dashboard.router)
api_router.include_router(comments.router)
api_router.include_router(conversations.router)
api_router.include_router(leads.router)
api_router.include_router(campaigns.router)
api_router.include_router(knowledge.router)
api_router.include_router(funnels.router)
api_router.include_router(content.router)
api_router.include_router(commerce.router)
api_router.include_router(logs.router)
api_router.include_router(settings.router)
