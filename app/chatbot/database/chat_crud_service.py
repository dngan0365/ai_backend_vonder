from typing import List, Dict, Optional, Any
from datetime import datetime, date
import json
from prisma.models import Trip, Event, Tour, Agency, Location, TripParticipants, SaveEvent
from app.db.prisma_client import prisma


class ChatbotDatabaseService:
    """Database service for chatbot queries"""
    
    # ==================== TRIP FUNCTIONS ====================
    
    @staticmethod
    async def search_trips(
        user_id: Optional[str] = None,
        location_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Search trips based on various criteria"""
        try:
            where_conditions = {}
            
            # Filter by user participation
            if user_id:
                where_conditions["participants"] = {
                    "some": {"userId": user_id}
                }
            
            # Filter by location
            if location_name:
                where_conditions["location"] = {
                    "name": {"contains": location_name, "mode": "insensitive"}
                }
            
            # Filter by date range
            if start_date:
                where_conditions["startDate"] = {"gte": start_date}
            if end_date:
                where_conditions["endDate"] = {"lte": end_date}
            
            trips = await prisma.trip.find_many(
                where=where_conditions,
                include={
                    "location": True,
                    "participants": {"include": {"user": True}}
                },
                take=limit,
                order_by={"createdAt": "desc"}
            )
            
            return [
                {
                    "id": trip.id,
                    "name": trip.name,
                    "description": trip.description,
                    "start_date": trip.startDate.strftime("%Y-%m-%d"),
                    "end_date": trip.endDate.strftime("%Y-%m-%d"),
                    "hotel_name": trip.hotelName,
                    "hotel_address": trip.hotelAddress,
                    "location": trip.location.name if trip.location else None,
                    "participants_count": len(trip.participants),
                    "participants": [p.user.name for p in trip.participants]
                }
                for trip in trips
            ]
        except Exception as e:
            print(f"Error searching trips: {e}")
            return []
    
    @staticmethod
    async def get_user_trips(user_id: str) -> List[Dict]:
        """Get all trips for a specific user"""
        try:
            trips = await prisma.trip.find_many(
                where={
                    "participants": {
                        "some": {"userId": user_id}
                    }
                },
                include={
                    "location": True,
                    "participants": {"include": {"user": True}}
                },
                order_by={"startDate": "desc"}
            )
            
            return [
                {
                    "id": trip.id,
                    "name": trip.name,
                    "description": trip.description,
                    "start_date": trip.startDate.strftime("%Y-%m-%d"),
                    "end_date": trip.endDate.strftime("%Y-%m-%d"),
                    "location": trip.location.name if trip.location else None,
                    "status": "upcoming" if trip.startDate > datetime.now() else "past"
                }
                for trip in trips
            ]
        except Exception as e:
            print(f"Error getting user trips: {e}")
            return []
    
    # ==================== EVENT FUNCTIONS ====================
    
    @staticmethod
    async def search_events(
        location_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Search events based on criteria"""
        try:
            where_conditions = {}
            
            # Filter by location
            if location_name:
                where_conditions["locations"] = {
                    "some": {
                        "location": {
                            "name": {"contains": location_name, "mode": "insensitive"}
                        }
                    }
                }
            
            # Filter by date range
            if start_date:
                where_conditions["startDate"] = {"gte": start_date}
            if end_date:
                where_conditions["endDate"] = {"lte": end_date}
            
            events = await prisma.event.find_many(
                where=where_conditions,
                include={
                    "locations": {"include": {"location": True}}
                },
                take=limit,
                order_by={"startDate": "asc"}
            )
            
            return [
                {
                    "id": event.id,
                    "name": event.name,
                    "description": event.description,
                    "cover_image": event.coverImage,
                    "start_date": event.startDate.strftime("%Y-%m-%d %H:%M"),
                    "end_date": event.endDate.strftime("%Y-%m-%d %H:%M"),
                    "locations": [
                        {
                            "name": el.location.name,
                            "description": el.description
                        }
                        for el in event.locations
                    ]
                }
                for event in events
            ]
        except Exception as e:
            print(f"Error searching events: {e}")
            return []
    
    @staticmethod
    async def get_user_saved_events(user_id: str) -> List[Dict]:
        """Get events saved by a user"""
        try:
            saved_events = await prisma.saveevent.find_many(
                where={"userId": user_id},
                include={
                    "event": {
                        "include": {
                            "locations": {"include": {"location": True}}
                        }
                    }
                },
                order_by={"createdAt": "desc"}
            )
            
            return [
                {
                    "id": se.event.id,
                    "name": se.event.name,
                    "description": se.event.description,
                    "start_date": se.event.startDate.strftime("%Y-%m-%d %H:%M"),
                    "end_date": se.event.endDate.strftime("%Y-%m-%d %H:%M"),
                    "saved_date": se.createdAt.strftime("%Y-%m-%d")
                }
                for se in saved_events
            ]
        except Exception as e:
            print(f"Error getting saved events: {e}")
            return []
    
    # ==================== TOUR FUNCTIONS ====================
    
    @staticmethod
    async def search_tours(
        location_name: Optional[str] = None,
        category: Optional[str] = None,
        province: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        max_duration: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Search tours based on various criteria"""
        try:
            where_conditions = {}
            
            # Filter by location
            if location_name:
                where_conditions["location"] = {
                    "name": {"contains": location_name, "mode": "insensitive"}
                }
            
            # Filter by category
            if category:
                where_conditions["category"] = category.upper()
            
            # Filter by province
            if province:
                where_conditions["province"] = province.upper()
            
            # Filter by price range
            if min_price is not None:
                where_conditions["price"] = {"gte": min_price}
            if max_price is not None:
                if "price" in where_conditions:
                    where_conditions["price"]["lte"] = max_price
                else:
                    where_conditions["price"] = {"lte": max_price}
            
            # Filter by duration
            if max_duration:
                where_conditions["duration"] = {"lte": max_duration}
            
            tours = await prisma.tour.find_many(
                where=where_conditions,
                include={
                    "agency": True,
                    "location": True
                },
                take=limit,
                order_by={"createdAt": "desc"}
            )
            
            return [
                {
                    "id": tour.id,
                    "title": tour.title,
                    "description": tour.description,
                    "price": tour.price,
                    "duration": f"{tour.duration} days",
                    "max_capacity": tour.maxCapacity,
                    "category": tour.category,
                    "province": tour.province,
                    "agency": {
                        "name": tour.agency.name,
                        "verified": tour.agency.verified
                    },
                    "location": tour.location.name if tour.location else None,
                    "available_dates": [date.strftime("%Y-%m-%d") for date in tour.startDates],
                    "includes": json.loads(tour.includes) if tour.includes else None,
                    "excludes": json.loads(tour.excludes) if tour.excludes else None
                }
                for tour in tours
            ]
        except Exception as e:
            print(f"Error searching tours: {e}")
            return []
    
    @staticmethod
    async def get_tour_details(tour_id: str) -> Dict:
        """Get detailed information about a specific tour"""
        try:
            tour = await prisma.tour.find_unique(
                where={"id": tour_id},
                include={
                    "agency": True,
                    "location": True,
                    "bookings": True
                }
            )
            
            if not tour:
                return {}
            
            return {
                "id": tour.id,
                "title": tour.title,
                "description": tour.description,
                "price": tour.price,
                "duration": f"{tour.duration} days",
                "max_capacity": tour.maxCapacity,
                "current_bookings": len(tour.bookings),
                "available_spots": tour.maxCapacity - len(tour.bookings),
                "images": tour.images,
                "itinerary": json.loads(tour.itinerary) if tour.itinerary else None,
                "includes": json.loads(tour.includes) if tour.includes else None,
                "excludes": json.loads(tour.excludes) if tour.excludes else None,
                "available_dates": [date.strftime("%Y-%m-%d") for date in tour.startDates],
                "agency": {
                    "name": tour.agency.name,
                    "description": tour.agency.description,
                    "verified": tour.agency.verified,
                    "website": tour.agency.website,
                    "phone": tour.agency.phoneNumber
                },
                "location": tour.location.name if tour.location else None
            }
        except Exception as e:
            print(f"Error getting tour details: {e}")
            return {}
    
    # ==================== AGENCY FUNCTIONS ====================
    
    @staticmethod
    async def search_agencies(
        name: Optional[str] = None,
        verified_only: bool = False,
        limit: int = 10
    ) -> List[Dict]:
        """Search travel agencies"""
        try:
            where_conditions = {}
            
            if name:
                where_conditions["name"] = {"contains": name, "mode": "insensitive"}
            
            if verified_only:
                where_conditions["verified"] = True
            
            agencies = await prisma.agency.find_many(
                where=where_conditions,
                include={
                    "tours": {"take": 5}  # Include first 5 tours
                },
                take=limit,
                order_by={"createdAt": "desc"}
            )
            
            return [
                {
                    "id": agency.id,
                    "name": agency.name,
                    "description": agency.description,
                    "verified": agency.verified,
                    "website": agency.website,
                    "phone": agency.phoneNumber,
                    "address": agency.address,
                    "logo": agency.logo,
                    "tours_count": len(agency.tours),
                    "sample_tours": [
                        {
                            "id": tour.id,
                            "title": tour.title,
                            "price": tour.price
                        }
                        for tour in agency.tours
                    ]
                }
                for agency in agencies
            ]
        except Exception as e:
            print(f"Error searching agencies: {e}")
            return []
    
    # ==================== GENERAL STATS FUNCTIONS ====================
    
    @staticmethod
    async def get_travel_statistics() -> Dict:
        """Get general travel statistics"""
        try:
            total_trips = await prisma.trip.count()
            total_events = await prisma.event.count()
            total_tours = await prisma.tour.count()
            total_agencies = await prisma.agency.count()
            verified_agencies = await prisma.agency.count(where={"verified": True})
            
            # Upcoming events
            upcoming_events = await prisma.event.count(
                where={"startDate": {"gte": datetime.now()}}
            )
            
            return {
                "total_trips": total_trips,
                "total_events": total_events,
                "upcoming_events": upcoming_events,
                "total_tours": total_tours,
                "total_agencies": total_agencies,
                "verified_agencies": verified_agencies,
                "verification_rate": round((verified_agencies / total_agencies * 100), 2) if total_agencies > 0 else 0
            }
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}
    
    @staticmethod
    async def get_popular_destinations(limit: int = 5) -> List[Dict]:
        """Get most popular travel destinations"""
        try:
            # This would require aggregation - simplified version
            locations = await prisma.location.find_many(
                include={
                    "trips": True,
                    "tours": True,
                    "events": {"include": {"event": True}}
                },
                take=limit
            )
            
            # Calculate popularity score
            popular_locations = []
            for location in locations:
                score = len(location.trips) + len(location.tours) + len(location.events)
                if score > 0:
                    popular_locations.append({
                        "name": location.name,
                        "trips_count": len(location.trips),
                        "tours_count": len(location.tours),
                        "events_count": len(location.events),
                        "popularity_score": score
                    })
            
            # Sort by popularity
            popular_locations.sort(key=lambda x: x["popularity_score"], reverse=True)
            return popular_locations[:limit]
            
        except Exception as e:
            print(f"Error getting popular destinations: {e}")
            return []


# Helper function to process natural language queries
def parse_chatbot_query(user_message: str) -> Dict[str, Any]:
    """Parse user message to determine query type and parameters"""
    message_lower = user_message.lower()
    
    query_info = {
        "type": "general",
        "parameters": {}
    }
    
    # Determine query type
    if any(word in message_lower for word in ["trip", "travel", "journey"]):
        query_info["type"] = "trips"
    elif any(word in message_lower for word in ["event", "festival", "happening"]):
        query_info["type"] = "events"
    elif any(word in message_lower for word in ["tour", "package", "booking"]):
        query_info["type"] = "tours"
    elif any(word in message_lower for word in ["agency", "company", "operator"]):
        query_info["type"] = "agencies"
    elif any(word in message_lower for word in ["statistic", "data", "number", "how many"]):
        query_info["type"] = "statistics"
    elif any(word in message_lower for word in ["popular", "best", "top", "recommend"]):
        query_info["type"] = "recommendations"
    
    # Extract parameters (simplified - you might want to use NLP libraries)
    if "price" in message_lower:
        # Extract price ranges, dates, etc.
        pass
    
    return query_info