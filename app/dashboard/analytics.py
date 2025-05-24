from datetime import datetime, timedelta
import json
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd
import numpy as np
from app.db.prisma_client import get_prisma
from app.config import settings

class DashboardAnalytics:
    """Analytics for dashboard"""
    
    @staticmethod
    async def get_user_growth(days: int = 30) -> List[Dict[str, Any]]:
        """Get user growth over time"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        async with get_prisma() as prisma:
            users = await prisma.user.find_many(
                where={
                    'createdAt': {
                        'gte': start_date
                    }
                },
                select={
                    'id': True,
                    'createdAt': True
                }
            )
        
        # Convert to dataframe
        if not users:
            return []
            
        df = pd.DataFrame([
            {'date': user['createdAt'].date(), 'count': 1}
            for user in users
        ])
        
        # Group by date and get counts
        if not df.empty:
            daily_counts = df.groupby('date').sum().reset_index()
            daily_counts['cumulative'] = daily_counts['count'].cumsum()
            
            # Fill in missing dates
            date_range = pd.date_range(start=start_date.date(), end=end_date.date())
            full_range = pd.DataFrame({'date': date_range})
            result = pd.merge(full_range, daily_counts, on='date', how='left').fillna(0)
            
            # Calculate cumulative correctly
            result['count'] = result['count'].astype(int)
            result['cumulative'] = result['count'].cumsum()
            
            return result.to_dict('records')
        
        return []
    
    @staticmethod
    async def get_top_locations(limit: int = 10) -> List[Dict[str, Any]]:
        """Get top locations by favorites"""
        async with get_prisma() as prisma:
            # Count favorites for each location
            locations = await prisma.location.find_many(
                include={
                    'favorites': True,
                    'blogs': True,
                    'trips': True
                }
            )
            
            # Calculate engagement score
            location_stats = [
                {
                    'id': loc.id,
                    'name': loc.name,
                    'category': loc.category,
                    'province': loc.province,
                    'favorites_count': len(loc.favorites),
                    'blogs_count': len(loc.blogs),
                    'trips_count': len(loc.trips),
                    'engagement_score': len(loc.favorites) + len(loc.blogs)*2 + len(loc.trips)*3
                }
                for loc in locations
            ]
            
            # Sort by engagement score
            location_stats.sort(key=lambda x: x['engagement_score'], reverse=True)
            
            return location_stats[:limit]
    
    @staticmethod
    async def get_blog_engagement() -> Dict[str, Any]:
        """Get blog engagement metrics"""
        async with get_prisma() as prisma:
            # Get all blogs with votes, comments, and replies
            blogs = await prisma.blog.find_many(
                include={
                    'votes': True,
                    'comments': {
                        'include': {
                            'votes': True,
                            'replies': {
                                'include': {
                                    'votes': True
                                }
                            }
                        }
                    }
                }
            )
            
            total_blogs = len(blogs)
            total_votes = sum(len(blog.votes) for blog in blogs)
            total_comments = sum(len(blog.comments) for blog in blogs)
            total_replies = sum(
                sum(len(comment.replies) for comment in blog.comments)
                for blog in blogs
            )
            
            # Calculate votes distribution
            upvotes = sum(1 for blog in blogs for vote in blog.votes if vote.type == 'UP')
            downvotes = total_votes - upvotes
            
            # Calculate engagement by category
            blog_categories = {}
            for blog in blogs:
                category = blog.category
                if category not in blog_categories:
                    blog_categories[category] = {
                        'count': 0,
                        'votes': 0,
                        'comments': 0,
                        'replies': 0
                    }
                
                blog_categories[category]['count'] += 1
                blog_categories[category]['votes'] += len(blog.votes)
                blog_categories[category]['comments'] += len(blog.comments)
                blog_categories[category]['replies'] += sum(len(comment.replies) for comment in blog.comments)
            
            # Calculate average engagement per blog
            avg_votes = total_votes / total_blogs if total_blogs > 0 else 0
            avg_comments = total_comments / total_blogs if total_blogs > 0 else 0
            avg_replies = total_replies / total_blogs if total_blogs > 0 else 0
            
            return {
                'total_blogs': total_blogs,
                'total_votes': total_votes,
                'total_comments': total_comments,
                'total_replies': total_replies,
                'upvotes': upvotes,
                'downvotes': downvotes,
                'avg_votes': round(avg_votes, 2),
                'avg_comments': round(avg_comments, 2),
                'avg_replies': round(avg_replies, 2),
                'categories': blog_categories
            }
    
    @staticmethod
    async def get_trip_analytics() -> Dict[str, Any]:
        """Get trip analytics"""
        async with get_prisma() as prisma:
            # Get all trips with participants
            trips = await prisma.trip.find_many(
                include={
                    'participants': True,
                    'location': True
                }
            )
            
            total_trips = len(trips)
            total_participants = sum(len(trip.participants) for trip in trips)
            
            # Calculate average participants per trip
            avg_participants = total_participants / total_trips if total_trips > 0 else 0
            
            # Location distribution
            location_counts = {}
            for trip in trips:
                location_name = trip.location.name
                if location_name not in location_counts:
                    location_counts[location_name] = 0
                location_counts[location_name] += 1
            
            # Sort locations by count
            top_locations = sorted(
                [{'name': name, 'count': count} for name, count in location_counts.items()],
                key=lambda x: x['count'],
                reverse=True
            )[:10]
            
            # Trip duration analysis
            durations = [(trip.endDate - trip.startDate).days + 1 for trip in trips]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                'total_trips': total_trips,
                'total_participants': total_participants,
                'avg_participants': round(avg_participants, 2),
                'avg_duration': round(avg_duration, 2),
                'top_locations': top_locations,
                'duration_distribution': {
                    '1-3 days': sum(1 for d in durations if 1 <= d <= 3),
                    '4-7 days': sum(1 for d in durations if 4 <= d <= 7),
                    '8-14 days': sum(1 for d in durations if 8 <= d <= 14),
                    '15+ days': sum(1 for d in durations if d >= 15)
                }
            }
    
    @staticmethod
    async def get_chatbot_usage() -> Dict[str, Any]:
        """Get chatbot usage analytics"""
        async with get_prisma() as prisma:
            # Get all chat sessions
            title_chats = await prisma.titlechat.find_many(
                include={
                    'chats': True,
                    'user': True
                }
            )
            
            total_sessions = len(title_chats)
            total_messages = sum(len(session.chats) for session in title_chats)
            
            # Average messages per session
            avg_messages = total_messages / total_sessions if total_sessions > 0 else 0
            
            # User distribution
            user_counts = {}
            for session in title_chats:
                user_name = session.user.name
                if user_name not in user_counts:
                    user_counts[user_name] = {
                        'sessions': 0,
                        'messages': 0
                    }
                user_counts[user_name]['sessions'] += 1
                user_counts[user_name]['messages'] += len(session.chats)
            
            # Top users by message count
            top_users = sorted(
                [{'name': name, 'sessions': data['sessions'], 'messages': data['messages']} 
                 for name, data in user_counts.items()],
                key=lambda x: x['messages'],
                reverse=True
            )[:10]
            
            # Chat volume over time
            chat_dates = [
                session.createdAt.date()
                for session in title_chats
            ]
            
            date_counts = {}
            for date in chat_dates:
                if date not in date_counts:
                    date_counts[date] = 0
                date_counts[date] += 1
            
            # Sort dates
            daily_chats = [
                {'date': date, 'count': count}
                for date, count in date_counts.items()
            ]
            daily_chats.sort(key=lambda x: x['date'])
            
            return {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'avg_messages': round(avg_messages, 2),
                'top_users': top_users,
                'daily_chats': daily_chats
            }