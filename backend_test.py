#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
import time

class ViralFlowAPITester:
    def __init__(self, base_url="https://ccclipmaker.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details="", response_data=None):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test_name": name,
            "success": success,
            "details": details,
            "response_data": response_data
        })

    def test_api_endpoint(self, name, method, endpoint, expected_status=200, data=None, params=None):
        """Test a single API endpoint"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            
            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if not success:
                details += f" (Expected: {expected_status})"
                if response.text:
                    details += f" - Response: {response.text[:200]}"
            
            response_data = None
            if success and response.text:
                try:
                    response_data = response.json()
                except:
                    response_data = response.text[:200]
            
            self.log_test(name, success, details, response_data)
            return success, response_data

        except requests.exceptions.Timeout:
            self.log_test(name, False, "Request timeout (30s)")
            return False, None
        except requests.exceptions.ConnectionError:
            self.log_test(name, False, "Connection error - server may be down")
            return False, None
        except Exception as e:
            self.log_test(name, False, f"Error: {str(e)}")
            return False, None

    def test_dashboard_stats(self):
        """Test dashboard stats endpoint"""
        print("\n🔍 Testing Dashboard Stats...")
        success, data = self.test_api_endpoint("Dashboard Stats", "GET", "stats")
        
        if success and data:
            required_fields = ['total_videos_discovered', 'total_clips_generated', 'total_posts_published']
            for field in required_fields:
                if field not in data:
                    self.log_test(f"Stats Field: {field}", False, "Missing required field")
                else:
                    self.log_test(f"Stats Field: {field}", True, f"Value: {data[field]}")
        
        return success

    def test_video_discovery(self):
        """Test video discovery endpoint"""
        print("\n🔍 Testing Video Discovery...")
        
        # Test basic discovery
        success, data = self.test_api_endpoint(
            "Video Discovery - Basic", 
            "GET", 
            "discover",
            params={"query": "music", "max_results": 5}
        )
        
        if success and data:
            if 'videos' in data and 'total' in data:
                self.log_test("Discovery Response Structure", True, f"Found {data['total']} videos")
                
                # Test video structure if videos found
                if data['videos'] and len(data['videos']) > 0:
                    video = data['videos'][0]
                    required_fields = ['id', 'title', 'channel', 'viral_score', 'views']
                    for field in required_fields:
                        if field in video:
                            self.log_test(f"Video Field: {field}", True, f"Value: {video[field]}")
                        else:
                            self.log_test(f"Video Field: {field}", False, "Missing field")
                    
                    return video['id'] if 'id' in video else None
                else:
                    self.log_test("Video Discovery Results", False, "No videos found")
            else:
                self.log_test("Discovery Response Structure", False, "Missing videos or total field")
        
        return None

    def test_video_details(self, video_id):
        """Test video details endpoint"""
        if not video_id:
            self.log_test("Video Details", False, "No video ID available")
            return False
            
        print(f"\n🔍 Testing Video Details for ID: {video_id}...")
        success, data = self.test_api_endpoint(
            "Video Details", 
            "GET", 
            f"videos/{video_id}"
        )
        
        if success and data:
            required_fields = ['id', 'title', 'channel', 'viral_score']
            for field in required_fields:
                if field in data:
                    self.log_test(f"Video Detail Field: {field}", True, f"Value: {data[field]}")
                else:
                    self.log_test(f"Video Detail Field: {field}", False, "Missing field")
        
        return success

    def test_clip_generation(self, video_id):
        """Test clip generation endpoint"""
        if not video_id:
            self.log_test("Clip Generation", False, "No video ID available")
            return None
            
        print(f"\n🔍 Testing Clip Generation for video: {video_id}...")
        
        clip_data = {
            "video_id": video_id,
            "start_time": 10,
            "duration": 30
        }
        
        success, data = self.test_api_endpoint(
            "Clip Generation", 
            "POST", 
            "clips/generate",
            expected_status=200,
            data=clip_data
        )
        
        if success and data:
            if 'clip_id' in data and 'success' in data:
                clip_id = data['clip_id']
                self.log_test("Clip Generation Response", True, f"Clip ID: {clip_id}")
                return clip_id
            else:
                self.log_test("Clip Generation Response", False, "Missing clip_id or success field")
        
        return None

    def test_clip_retrieval(self, clip_id):
        """Test clip retrieval endpoint"""
        if not clip_id:
            self.log_test("Clip Retrieval", False, "No clip ID available")
            return False
            
        print(f"\n🔍 Testing Clip Retrieval for ID: {clip_id}...")
        success, data = self.test_api_endpoint(
            "Clip Retrieval", 
            "GET", 
            f"clips/{clip_id}"
        )
        
        if success and data:
            required_fields = ['clip_id', 'video_id', 'start_time', 'duration', 'status']
            for field in required_fields:
                if field in data:
                    self.log_test(f"Clip Field: {field}", True, f"Value: {data[field]}")
                else:
                    self.log_test(f"Clip Field: {field}", False, "Missing field")
        
        return success

    def test_social_posting(self, clip_id):
        """Test social media posting endpoint"""
        if not clip_id:
            self.log_test("Social Posting", False, "No clip ID available")
            return False
            
        print(f"\n🔍 Testing Social Media Posting for clip: {clip_id}...")
        
        post_data = {
            "clip_id": clip_id,
            "caption": "Test viral content! 🎬",
            "platforms": ["youtube", "instagram"],
            "hashtags": "#viral #test"
        }
        
        success, data = self.test_api_endpoint(
            "Social Media Posting", 
            "POST", 
            "post",
            data=post_data
        )
        
        if success and data:
            if 'success' in data and 'posts' in data:
                self.log_test("Posting Response", True, f"Posted to {len(data['posts'])} platforms")
            else:
                self.log_test("Posting Response", False, "Missing success or posts field")
        
        return success

    def test_post_history(self):
        """Test post history endpoint"""
        print("\n🔍 Testing Post History...")
        success, data = self.test_api_endpoint("Post History", "GET", "history")
        
        if success and data:
            if 'posts' in data and 'total' in data:
                self.log_test("History Response Structure", True, f"Found {data['total']} posts")
            else:
                self.log_test("History Response Structure", False, "Missing posts or total field")
        
        return success

    def test_api_keys_management(self):
        """Test API keys management endpoints"""
        print("\n🔍 Testing API Keys Management...")
        
        # Test getting API keys
        success, data = self.test_api_endpoint("Get API Keys", "GET", "settings/api-keys")
        
        # Test saving API keys
        keys_data = {
            "youtube_api_key": "test_youtube_key_123",
            "instagram_access_token": "test_instagram_token_456"
        }
        
        success2, data2 = self.test_api_endpoint(
            "Save API Keys", 
            "POST", 
            "settings/api-keys",
            data=keys_data
        )
        
        return success and success2

    def test_error_handling(self):
        """Test error handling for invalid requests"""
        print("\n🔍 Testing Error Handling...")
        
        # Test invalid video ID
        self.test_api_endpoint(
            "Invalid Video ID", 
            "GET", 
            "videos/invalid_id_12345",
            expected_status=404
        )
        
        # Test invalid clip generation
        invalid_clip_data = {
            "video_id": "invalid_id",
            "start_time": -10,  # Invalid start time
            "duration": 5       # Invalid duration (too short)
        }
        
        self.test_api_endpoint(
            "Invalid Clip Generation", 
            "POST", 
            "clips/generate",
            expected_status=400,
            data=invalid_clip_data
        )

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting ViralFlow Studio API Tests...")
        print(f"Testing against: {self.base_url}")
        
        start_time = time.time()
        
        # Test basic endpoints
        self.test_dashboard_stats()
        
        # Test video discovery and get a video ID
        video_id = self.test_video_discovery()
        
        # Test video details if we have a video ID
        if video_id:
            self.test_video_details(video_id)
            
            # Test clip generation and get clip ID
            clip_id = self.test_clip_generation(video_id)
            
            # Test clip retrieval if we have a clip ID
            if clip_id:
                # Wait a bit for clip processing
                print("⏳ Waiting for clip processing...")
                time.sleep(3)
                self.test_clip_retrieval(clip_id)
                
                # Test social posting
                self.test_social_posting(clip_id)
        
        # Test other endpoints
        self.test_post_history()
        self.test_api_keys_management()
        
        # Test error handling
        self.test_error_handling()
        
        # Print summary
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        print(f"\n📊 Test Summary:")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {round((self.tests_passed / self.tests_run) * 100, 1)}%")
        print(f"Duration: {duration}s")
        
        return self.tests_passed == self.tests_run

def main():
    tester = ViralFlowAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": tester.tests_run,
        "passed_tests": tester.tests_passed,
        "success_rate": round((tester.tests_passed / tester.tests_run) * 100, 1) if tester.tests_run > 0 else 0,
        "test_details": tester.test_results
    }
    
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: /app/backend_test_results.json")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())