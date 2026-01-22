"""
Video Transcript API Tests
Tests for the /api/video/transcript/{video_id} endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestVideoTranscriptAPI:
    """Tests for video transcript endpoints"""
    
    def test_transcript_endpoint_returns_json_structure(self):
        """Test that transcript endpoint returns proper JSON structure"""
        # Use a well-known video ID that has captions
        video_id = "dQw4w9WgXcQ"
        response = requests.get(f"{BASE_URL}/api/video/transcript/{video_id}")
        
        # Should return 200 OK
        assert response.status_code == 200
        
        data = response.json()
        
        # Must have these fields regardless of success/failure
        assert "success" in data
        assert "video_id" in data
        assert data["video_id"] == video_id
        
    def test_transcript_success_response_structure(self):
        """Test successful transcript response has all required fields"""
        video_id = "dQw4w9WgXcQ"
        response = requests.get(f"{BASE_URL}/api/video/transcript/{video_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        if data.get("success"):
            # Successful response should have these fields
            assert "language" in data
            assert "word_count" in data
            assert "full_text" in data
            assert "segments" in data
            assert "total_segments" in data
            
            # Validate data types
            assert isinstance(data["word_count"], int)
            assert isinstance(data["full_text"], str)
            assert isinstance(data["segments"], list)
            assert isinstance(data["total_segments"], int)
            
            # Word count should be positive
            assert data["word_count"] > 0
            
            # Full text should not be empty
            assert len(data["full_text"]) > 0
            
            print(f"SUCCESS: Transcript loaded with {data['word_count']} words")
        else:
            # Error response should have error field
            assert "error" in data
            print(f"INFO: Transcript blocked/unavailable - error handling works: {data['error'][:100]}...")
    
    def test_transcript_error_response_structure(self):
        """Test error response has proper structure"""
        # Use an invalid video ID
        video_id = "invalid_video_id_12345"
        response = requests.get(f"{BASE_URL}/api/video/transcript/{video_id}")
        
        assert response.status_code == 200  # API returns 200 with error in body
        data = response.json()
        
        # Error response structure
        assert "success" in data
        assert data["success"] == False
        assert "error" in data
        assert "video_id" in data
        assert data["video_id"] == video_id
        
        print(f"SUCCESS: Error response properly structured")
    
    def test_transcript_blocked_response_structure(self):
        """Test that blocked requests return proper error structure"""
        # This video may be blocked from cloud IPs
        video_id = "jfl8N5pPAVU"
        response = requests.get(f"{BASE_URL}/api/video/transcript/{video_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have proper structure
        assert "success" in data
        assert "video_id" in data
        
        if not data.get("success"):
            assert "error" in data
            # Error message should be informative
            assert len(data["error"]) > 0
            print(f"INFO: Video blocked as expected - error: {data['error'][:100]}...")
        else:
            print(f"SUCCESS: Transcript loaded with {data.get('word_count', 0)} words")
    
    def test_cached_transcript_endpoint(self):
        """Test cached transcript endpoint"""
        video_id = "dQw4w9WgXcQ"
        response = requests.get(f"{BASE_URL}/api/video/transcript/{video_id}/cached")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have success field
        assert "success" in data
        
        if data.get("success"):
            assert "cached" in data
            assert data["cached"] == True
            assert "video_id" in data
            print(f"SUCCESS: Cached transcript found")
        else:
            # No cached transcript is also valid
            assert "error" in data or "cached" in data
            print(f"INFO: No cached transcript - this is expected for first request")
    
    def test_transcript_segments_structure(self):
        """Test that transcript segments have proper structure"""
        video_id = "dQw4w9WgXcQ"
        response = requests.get(f"{BASE_URL}/api/video/transcript/{video_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        if data.get("success") and data.get("segments"):
            segments = data["segments"]
            assert len(segments) > 0
            
            # Check first segment structure
            segment = segments[0]
            assert "text" in segment
            assert "start" in segment
            assert "duration" in segment
            assert "start_formatted" in segment
            
            # Validate types
            assert isinstance(segment["text"], str)
            assert isinstance(segment["start"], (int, float))
            assert isinstance(segment["duration"], (int, float))
            assert isinstance(segment["start_formatted"], str)
            
            print(f"SUCCESS: Segments properly structured ({len(segments)} segments)")
        else:
            print(f"INFO: No segments available (video may be blocked)")


class TestTranscriptEndpointNoAuth:
    """Test that transcript endpoints don't require authentication"""
    
    def test_transcript_no_auth_required(self):
        """Transcript endpoint should work without authentication"""
        video_id = "dQw4w9WgXcQ"
        # Make request without any auth headers
        response = requests.get(f"{BASE_URL}/api/video/transcript/{video_id}")
        
        # Should not return 401 Unauthorized
        assert response.status_code != 401
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        print(f"SUCCESS: Transcript endpoint accessible without auth")
    
    def test_cached_transcript_no_auth_required(self):
        """Cached transcript endpoint should work without authentication"""
        video_id = "dQw4w9WgXcQ"
        response = requests.get(f"{BASE_URL}/api/video/transcript/{video_id}/cached")
        
        assert response.status_code != 401
        assert response.status_code == 200
        print(f"SUCCESS: Cached transcript endpoint accessible without auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
