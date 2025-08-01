"""
Performance tests for the application.
Tests for response times, memory usage, database query efficiency, etc.
"""

import pytest
import time
import json
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from app import create_app
from app.database import db
from app.database.models import Prospect, DataSource, GoNoGoDecision


@pytest.fixture(scope="function")
def app():
    """Create a test Flask application with in-memory database."""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp()
    
    # Create app with test configuration
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    os.environ['USER_DATABASE_URL'] = f'sqlite:///{db_path}'
    os.environ['TESTING'] = 'True'
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create a test data source
        test_source = DataSource(
            name='Test Agency',
            url='https://test.gov', 
            scraper_class='TestScraper',
            active=True
        )
        db.session.add(test_source)
        db.session.commit()
        
        app.config['TEST_SOURCE_ID'] = test_source.id
        app.config['TEST_USER_ID'] = 'test-user-123'
        
        yield app
        
        db.session.remove()
        db.drop_all()
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def auth_client(app, client):
    """Create an authenticated test client."""
    with patch('app.api.auth.get_current_user') as mock_auth:
        mock_auth.return_value = {
            'id': app.config['TEST_USER_ID'],
            'username': 'testuser',
            'role': 'user'
        }
        yield client


@pytest.fixture
def large_dataset(app):
    """Create a large dataset for performance testing."""
    with app.app_context():
        # Create 1000 test prospects
        prospects = []
        
        for i in range(1000):
            prospect_data = {
                'id': f'PERF-{i:06d}',
                'title': f'Performance Test Contract {i}',
                'description': f'Test description for performance testing contract number {i}. ' + 
                             'This is a longer description to simulate real-world data. ' * 3,
                'agency': f'Test Agency {i % 10}',  # 10 different agencies
                'posted_date': f'2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}',
                'estimated_value': 10000 + (i * 1000),
                'estimated_value_text': f'${(10000 + (i * 1000)):,}',
                'naics': f'54151{i % 10}',  # Vary NAICS codes
                'source_data_id': app.config['TEST_SOURCE_ID'],
                'source_file': f'perf_test_{i // 100}.json',
                'loaded_at': datetime.now(timezone.utc)
            }
            
            # Add some AI enhancement data to some prospects
            if i % 10 == 0:
                prospect_data.update({
                    'ai_enhanced_title': f'Enhanced: {prospect_data["title"]}',
                    'ai_enhanced_description': f'AI Enhanced: {prospect_data["description"]}',
                    'ollama_processed_at': datetime.now(timezone.utc)
                })
            
            add_prospect(prospect_data)
        
        db.session.commit()
        
        return 1000


class TestAPIResponseTimes:
    """Test API response times under various conditions."""
    
    def test_prospects_api_base_performance(self, client):
        """Test basic prospects API response time."""
        start_time = time.time()
        response = client.get('/api/prospects')
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Should respond within 1 second for basic query
        response_time = end_time - start_time
        assert response_time < 1.0, f"Response time {response_time:.3f}s exceeds 1.0s threshold"
    
    def test_prospects_api_large_dataset_performance(self, client, large_dataset):
        """Test prospects API performance with large dataset."""
        start_time = time.time()
        response = client.get('/api/prospects?limit=50')
        end_time = time.time()
        
        assert response.status_code == 200
        
        data = response.get_json()
        assert len(data['prospects']) == 50
        assert data['pagination']['total_items'] == large_dataset
        
        # Should respond within 2 seconds even with large dataset
        response_time = end_time - start_time
        assert response_time < 2.0, f"Response time {response_time:.3f}s exceeds 2.0s threshold"
    
    def test_prospects_api_search_performance(self, client, large_dataset):
        """Test search performance with large dataset."""
        start_time = time.time()
        response = client.get('/api/prospects?keywords=Performance Test')
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Should respond within 3 seconds for search query
        response_time = end_time - start_time
        assert response_time < 3.0, f"Search response time {response_time:.3f}s exceeds 3.0s threshold"
        
        data = response.get_json()
        # Should return some results
        assert len(data['prospects']) > 0
    
    def test_prospects_api_complex_filter_performance(self, client, large_dataset):
        """Test complex filtering performance."""
        start_time = time.time()
        response = client.get('/api/prospects?agency=Test Agency 1&naics=541511&keywords=contract')
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Should respond within 3 seconds for complex query
        response_time = end_time - start_time
        assert response_time < 3.0, f"Complex filter response time {response_time:.3f}s exceeds 3.0s threshold"
    
    def test_prospects_api_pagination_performance(self, client, large_dataset):
        """Test pagination performance."""
        # Test multiple page requests
        total_time = 0
        
        for page in range(1, 6):  # Test first 5 pages
            start_time = time.time()
            response = client.get(f'/api/prospects?page={page}&limit=20')
            end_time = time.time()
            
            assert response.status_code == 200
            
            page_time = end_time - start_time
            total_time += page_time
            
            # Each page should respond quickly
            assert page_time < 1.5, f"Page {page} response time {page_time:.3f}s exceeds 1.5s threshold"
        
        # Average page load time should be reasonable
        avg_time = total_time / 5
        assert avg_time < 1.0, f"Average page load time {avg_time:.3f}s exceeds 1.0s threshold"


class TestDatabasePerformance:
    """Test database query performance."""
    
    def test_prospect_bulk_creation_performance(self, app):
        """Test bulk prospect creation performance."""
        with app.app_context():
            start_time = time.time()
            
            # Create 100 prospects in bulk
            prospects = []
            for i in range(100):
                prospect_data = {
                    'id': f'BULK-{i:04d}',
                    'title': f'Bulk Test Contract {i}',
                    'description': f'Test description {i}',
                    'agency': 'Bulk Test Agency',
                    'posted_date': '2024-01-15',
                    'estimated_value': 50000,
                    'estimated_value_text': '$50,000',
                    'naics': '541511',
                    'source_data_id': app.config['TEST_SOURCE_ID'],
                    'source_file': 'bulk_test.json',
                    'loaded_at': datetime.now(timezone.utc)
                }
                add_prospect(prospect_data)
            
            db.session.commit()
            end_time = time.time()
            
            creation_time = end_time - start_time
            # Should create 100 prospects in under 5 seconds
            assert creation_time < 5.0, f"Bulk creation time {creation_time:.3f}s exceeds 5.0s threshold"
            
            # Calculate rate
            rate = 100 / creation_time
            assert rate > 20, f"Creation rate {rate:.1f} prospects/sec is below 20/sec threshold"
    
    def test_duplicate_detection_performance(self, app, large_dataset):
        """Test duplicate detection performance with large dataset."""
        with app.app_context():
            from app.services.duplicate_detection import find_duplicates
            
            # Create a new prospect that might have duplicates
            test_prospect_data = {
                'id': 'DUP-TEST-001',
                'title': 'Performance Test Contract 100',  # Similar to existing
                'description': 'Test description for performance',
                'agency': 'Test Agency 0',
                'posted_date': '2024-01-15',
                'estimated_value': 110000,
                'estimated_value_text': '$110,000',
                'naics': '541510',
                'source_data_id': app.config['TEST_SOURCE_ID'],
                'source_file': 'dup_test.json',
                'loaded_at': datetime.now(timezone.utc)
            }
            
            add_prospect(test_prospect_data)
            db.session.commit()
            
            start_time = time.time()
            duplicates = find_duplicates('DUP-TEST-001')
            end_time = time.time()
            
            detection_time = end_time - start_time
            # Should find duplicates in under 2 seconds even with large dataset
            assert detection_time < 2.0, f"Duplicate detection time {detection_time:.3f}s exceeds 2.0s threshold"
            
            # Should return some results
            assert isinstance(duplicates, list)


class TestDecisionPerformance:
    """Test decision creation and retrieval performance."""
    
    def test_decision_creation_performance(self, app, auth_client, large_dataset):
        """Test decision creation performance."""
        with app.app_context():
            # Create a test prospect for decisions
            prospect_data = {
                'id': 'DECISION-PERF-001',
                'title': 'Decision Performance Test',
                'description': 'Test prospect for decision performance',
                'agency': 'Test Agency',
                'posted_date': '2024-01-15',
                'estimated_value': 75000,
                'estimated_value_text': '$75,000',
                'naics': '541511',
                'source_data_id': app.config['TEST_SOURCE_ID'],
                'source_file': 'decision_perf_test.json',
                'loaded_at': datetime.now(timezone.utc)
            }
            add_prospect(prospect_data)
            db.session.commit()
        
        # Test bulk decision creation
        start_time = time.time()
        
        for i in range(50):
            decision_data = {
                'prospect_id': 'DECISION-PERF-001',
                'decision': 'go' if i % 2 == 0 else 'no-go',
                'reason': f'Performance test decision {i}'
            }
            
            response = auth_client.post('/api/decisions/',
                                      data=json.dumps(decision_data),
                                      content_type='application/json')
            assert response.status_code == 201
        
        end_time = time.time()
        
        total_time = end_time - start_time
        # Should create 50 decisions in under 10 seconds
        assert total_time < 10.0, f"Decision creation time {total_time:.3f}s exceeds 10.0s threshold"
        
        # Calculate rate
        rate = 50 / total_time
        assert rate > 5, f"Decision creation rate {rate:.1f} decisions/sec is below 5/sec threshold"
    
    def test_decision_retrieval_performance(self, app, auth_client):
        """Test decision retrieval performance with many decisions."""
        with app.app_context():
            # Create test prospect and many decisions
            prospect_data = {
                'id': 'DECISION-RETRIEVAL-001',
                'title': 'Decision Retrieval Test',
                'description': 'Test prospect for decision retrieval',
                'agency': 'Test Agency',
                'posted_date': '2024-01-15',
                'estimated_value': 50000,
                'estimated_value_text': '$50,000',
                'naics': '541511',
                'source_data_id': app.config['TEST_SOURCE_ID'],
                'source_file': 'decision_retrieval_test.json',
                'loaded_at': datetime.now(timezone.utc)
            }
            add_prospect(prospect_data)
            
            # Create 100 decisions directly in database for speed
            from app.database.user_models import User
            
            test_user = User(
                id=app.config['TEST_USER_ID'],
                username='testuser',
                email='test@example.com',
                first_name='Test',
                last_name='User'
            )
            db.session.add(test_user)
            
            for i in range(100):
                decision = Decision(
                    prospect_id='DECISION-RETRIEVAL-001',
                    user_id=app.config['TEST_USER_ID'],
                    decision='go' if i % 2 == 0 else 'no-go',
                    reason=f'Test decision {i}',
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(decision)
            
            db.session.commit()
        
        # Test retrieval performance
        start_time = time.time()
        response = auth_client.get('/api/decisions/DECISION-RETRIEVAL-001')
        end_time = time.time()
        
        assert response.status_code == 200
        
        retrieval_time = end_time - start_time
        # Should retrieve 100 decisions in under 1 second
        assert retrieval_time < 1.0, f"Decision retrieval time {retrieval_time:.3f}s exceeds 1.0s threshold"
        
        data = response.get_json()
        assert data['data']['total_decisions'] == 100


class TestMemoryUsage:
    """Test memory usage patterns."""
    
    def test_api_memory_efficiency(self, client, large_dataset):
        """Test that API calls don't cause memory leaks."""
        import gc
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make many API calls
        for i in range(50):
            response = client.get('/api/prospects?limit=20')
            assert response.status_code == 200
            
            # Force garbage collection every 10 requests
            if i % 10 == 0:
                gc.collect()
        
        # Check final memory usage
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 50MB)
        max_growth = 50 * 1024 * 1024  # 50MB in bytes
        assert memory_growth < max_growth, f"Memory growth {memory_growth / 1024 / 1024:.1f}MB exceeds 50MB threshold"


class TestConcurrencyPerformance:
    """Test performance under concurrent load."""
    
    def test_concurrent_api_requests(self, client):
        """Test API performance under concurrent requests."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            start_time = time.time()
            response = client.get('/api/prospects')
            end_time = time.time()
            
            results.put({
                'status_code': response.status_code,
                'response_time': end_time - start_time
            })
        
        # Create 10 concurrent threads
        threads = []
        start_time = time.time()
        
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Collect results
        response_times = []
        while not results.empty():
            result = results.get()
            assert result['status_code'] == 200
            response_times.append(result['response_time'])
        
        # All 10 requests should complete within 5 seconds
        assert total_time < 5.0, f"Concurrent requests took {total_time:.3f}s, exceeds 5.0s threshold"
        
        # Average response time should be reasonable
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 2.0, f"Average response time {avg_response_time:.3f}s exceeds 2.0s threshold"
        
        # No request should take too long
        max_response_time = max(response_times)
        assert max_response_time < 3.0, f"Max response time {max_response_time:.3f}s exceeds 3.0s threshold"


class TestScalabilityLimits:
    """Test application behavior at scale limits."""
    
    def test_large_page_size_handling(self, client, large_dataset):
        """Test handling of large page sizes."""
        # Test maximum reasonable page size
        response = client.get('/api/prospects?limit=500')
        
        if response.status_code == 200:
            # Should handle large page size efficiently
            start_time = time.time()
            data = response.get_json()
            end_time = time.time()
            
            processing_time = end_time - start_time
            assert processing_time < 1.0, f"Large page processing took {processing_time:.3f}s"
            
            # Should return expected number of results
            assert len(data['prospects']) <= 500
        else:
            # Should reject gracefully if limit is too high
            assert response.status_code == 400
    
    def test_deep_pagination_performance(self, client, large_dataset):
        """Test performance of deep pagination."""
        # Test accessing a page deep in the results
        page_number = 40  # Page 40 with 20 items per page = item 800
        
        start_time = time.time()
        response = client.get(f'/api/prospects?page={page_number}&limit=20')
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Deep pagination should still be reasonably fast
        response_time = end_time - start_time
        assert response_time < 2.0, f"Deep pagination response time {response_time:.3f}s exceeds 2.0s threshold"
        
        data = response.get_json()
        assert data['pagination']['page'] == page_number


if __name__ == '__main__':
    # Run with specific performance markers
    pytest.main([__file__, '-v', '--tb=short'])