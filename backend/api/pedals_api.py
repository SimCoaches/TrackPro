"""
Pedals API Router for TrackPro Backend
Wraps the existing pedals module functionality
"""
import sys
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import logging

# Add trackpro to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "trackpro"))

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from auth_middleware import get_current_user, get_current_user_optional

logger = logging.getLogger(__name__)

# Import existing TrackPro pedals modules
try:
    from pedals.hardware_input import HardwareInput
    from pedals.calibration import CalibrationManager
    from pedals.curve_cache import CurveCache
    from pedals.output import OutputManager
    from pedals.profile_dialog import ProfileManager
except ImportError as e:
    logger.warning(f"Could not import pedals modules: {e}")
    HardwareInput = None
    CalibrationManager = None
    CurveCache = None
    OutputManager = None
    ProfileManager = None

router = APIRouter()

# Request/Response Models
class PedalStatusResponse(BaseModel):
    connected: bool
    device_name: Optional[str] = None
    raw_values: Dict[str, float] = {}
    calibrated_values: Dict[str, float] = {}
    timestamp: str

class CalibrationRequest(BaseModel):
    pedal_type: str  # "throttle", "brake", "clutch"
    curve_type: str  # "linear", "s-curve", etc.
    points: List[Dict[str, float]]  # calibration points

class ProfileRequest(BaseModel):
    name: str
    description: Optional[str] = None
    calibration_data: Dict[str, Any]

class ProfileResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    calibration_data: Dict[str, Any]
    created_at: str
    updated_at: str

# Service wrapper class
class PedalsService:
    """Service wrapper for existing pedals functionality"""
    
    def __init__(self):
        self.hardware_input = None
        self.calibration_manager = None
        self.curve_cache = None
        self.output_manager = None
        self.profile_manager = None
        self.streaming_task = None
        self._initialize_modules()
    
    def _initialize_modules(self):
        """Initialize existing pedals modules"""
        try:
            if HardwareInput:
                self.hardware_input = HardwareInput()
            if CalibrationManager:
                self.calibration_manager = CalibrationManager()
            if CurveCache:
                self.curve_cache = CurveCache()
            if OutputManager:
                self.output_manager = OutputManager()
            if ProfileManager:
                self.profile_manager = ProfileManager()
                
            logger.info("Pedals service modules initialized")
        except Exception as e:
            logger.error(f"Error initializing pedals modules: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current pedal status"""
        try:
            if not self.hardware_input:
                return {
                    "connected": False,
                    "error": "Hardware input not available"
                }
            
            # Get current values from hardware
            raw_values = await self._get_raw_values()
            calibrated_values = await self._get_calibrated_values(raw_values)
            
            return {
                "connected": True,
                "device_name": getattr(self.hardware_input, 'device_name', 'Unknown'),
                "raw_values": raw_values,
                "calibrated_values": calibrated_values,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting pedal status: {e}")
            return {
                "connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _get_raw_values(self) -> Dict[str, float]:
        """Get raw pedal values"""
        try:
            if hasattr(self.hardware_input, 'get_values'):
                return await self.hardware_input.get_values()
            return {}
        except Exception as e:
            logger.error(f"Error getting raw values: {e}")
            return {}
    
    async def _get_calibrated_values(self, raw_values: Dict[str, float]) -> Dict[str, float]:
        """Get calibrated pedal values"""
        try:
            if not self.calibration_manager:
                return raw_values
            
            calibrated = {}
            for pedal, raw_value in raw_values.items():
                calibrated[pedal] = await self.calibration_manager.calibrate_value(pedal, raw_value)
            
            return calibrated
        except Exception as e:
            logger.error(f"Error getting calibrated values: {e}")
            return raw_values
    
    async def start_calibration(self, pedal_type: str, curve_type: str, points: List[Dict[str, float]]) -> Dict[str, Any]:
        """Start pedal calibration"""
        try:
            if not self.calibration_manager:
                raise HTTPException(status_code=503, detail="Calibration manager not available")
            
            result = await self.calibration_manager.start_calibration(
                pedal_type=pedal_type,
                curve_type=curve_type,
                points=points
            )
            
            return {
                "status": "calibration_started",
                "pedal_type": pedal_type,
                "curve_type": curve_type,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error starting calibration: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def save_profile(self, name: str, description: Optional[str], calibration_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save calibration profile"""
        try:
            if not self.profile_manager:
                raise HTTPException(status_code=503, detail="Profile manager not available")
            
            profile_id = await self.profile_manager.save_profile(
                name=name,
                description=description,
                calibration_data=calibration_data
            )
            
            return {
                "id": profile_id,
                "name": name,
                "description": description,
                "status": "saved",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def load_profile(self, profile_id: str) -> Dict[str, Any]:
        """Load calibration profile"""
        try:
            if not self.profile_manager:
                raise HTTPException(status_code=503, detail="Profile manager not available")
            
            profile = await self.profile_manager.load_profile(profile_id)
            
            if not profile:
                raise HTTPException(status_code=404, detail="Profile not found")
            
            return profile
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error loading profile: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# Global service instance
pedals_service = PedalsService()

# API Endpoints
@router.get("/status", response_model=PedalStatusResponse)
async def get_pedal_status(user_id: Optional[str] = Depends(get_current_user_optional)):
    """Get current pedal hardware status"""
    status = await pedals_service.get_status()
    return PedalStatusResponse(**status)

@router.post("/calibrate")
async def start_calibration(
    request: CalibrationRequest,
    user_id: str = Depends(get_current_user)
):
    """Start pedal calibration process"""
    result = await pedals_service.start_calibration(
        pedal_type=request.pedal_type,
        curve_type=request.curve_type,
        points=request.points
    )
    return result

@router.get("/profiles")
async def get_profiles(user_id: str = Depends(get_current_user)):
    """Get all calibration profiles for the user"""
    try:
        if not pedals_service.profile_manager:
            raise HTTPException(status_code=503, detail="Profile manager not available")
        
        profiles = await pedals_service.profile_manager.get_user_profiles(user_id)
        return {"profiles": profiles}
        
    except Exception as e:
        logger.error(f"Error getting profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/profiles", response_model=ProfileResponse)
async def save_profile(
    request: ProfileRequest,
    user_id: str = Depends(get_current_user)
):
    """Save a new calibration profile"""
    result = await pedals_service.save_profile(
        name=request.name,
        description=request.description,
        calibration_data=request.calibration_data
    )
    return ProfileResponse(**result)

@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get a specific calibration profile"""
    profile = await pedals_service.load_profile(profile_id)
    return ProfileResponse(**profile)

@router.put("/profiles/{profile_id}")
async def update_profile(
    profile_id: str,
    request: ProfileRequest,
    user_id: str = Depends(get_current_user)
):
    """Update an existing calibration profile"""
    try:
        if not pedals_service.profile_manager:
            raise HTTPException(status_code=503, detail="Profile manager not available")
        
        result = await pedals_service.profile_manager.update_profile(
            profile_id=profile_id,
            name=request.name,
            description=request.description,
            calibration_data=request.calibration_data
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/profiles/{profile_id}")
async def delete_profile(
    profile_id: str,
    user_id: str = Depends(get_current_user)
):
    """Delete a calibration profile"""
    try:
        if not pedals_service.profile_manager:
            raise HTTPException(status_code=503, detail="Profile manager not available")
        
        await pedals_service.profile_manager.delete_profile(profile_id)
        
        return {"status": "deleted", "profile_id": profile_id}
        
    except Exception as e:
        logger.error(f"Error deleting profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream/start")
async def start_pedal_streaming(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Start real-time pedal data streaming"""
    try:
        # TODO: Implement WebSocket streaming
        # This will be connected with the connection manager for real-time data
        
        return {
            "status": "streaming_started",
            "message": "Real-time pedal data streaming will be available via WebSocket",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting pedal streaming: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream/stop")
async def stop_pedal_streaming(user_id: str = Depends(get_current_user)):
    """Stop real-time pedal data streaming"""
    try:
        # TODO: Implement WebSocket streaming stop
        
        return {
            "status": "streaming_stopped",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error stopping pedal streaming: {e}")
        raise HTTPException(status_code=500, detail=str(e))