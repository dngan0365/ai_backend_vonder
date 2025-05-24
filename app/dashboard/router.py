from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
import logging

from app.config import settings
from app.auth.router import get_current_user
from app.dashboard.analytics import DashboardAnalytics

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/user-growth")
async def get_user_growth(
    days: int = 30,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get user growth over time"""
    # Check if user is admin
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    try:
        result = await DashboardAnalytics.get_user_growth(days)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user growth: {str(e)}"
        )

@router.get("/top-locations")
async def get_top_locations(
    limit: int = 10,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get top locations by popularity"""
    logger = logging.getLogger(settings.DATABASE_URL)
    try:
        result = await DashboardAnalytics.get_top_locations(limit)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching top locations: {str(e)}"
        )

@router.get("/blog-engagement")
async def get_blog_engagement(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get blog engagement metrics"""
    try:
        result = await DashboardAnalytics.get_blog_engagement()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching blog engagement: {str(e)}"
        )

@router.get("/trip-analytics")
async def get_trip_analytics(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get trip analytics"""
    try:
        result = await DashboardAnalytics.get_trip_analytics()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching trip analytics: {str(e)}"
        )

@router.get("/chatbot-usage")
async def get_chatbot_usage(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get chatbot usage analytics"""
    # Check if user is admin
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    try:
        result = await DashboardAnalytics.get_chatbot_usage()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching chatbot usage: {str(e)}"
        )