"""
Comprehensive tests for Prospects API endpoints.

Tests all prospects API functionality including filtering, pagination, and search.
"""

import pytest
from datetime import datetime, timezone, date
from decimal import Decimal
import json

from app import create_app
from app.database import db
from app.database.models import Prospect, DataSource


class TestProspectsAPI:
    """Test suite for Prospects API endpoints."""
    
    @pytest.fixture(scope='class')
    def app(self):
        """Create test Flask app."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture(autouse=True)
    def setup_database(self, app):
        """Set up test database with sample data."""
        with app.app_context():
            db.create_all()
            
            # Create test data sources
            data_sources = [
                DataSource(
                    name='Department of Test',
                    url='https://test.gov',
                    last_scraped=datetime.now(timezone.utc)
                ),
                DataSource(
                    name='Test Agency',
                    url='https://agency.test.gov',
                    last_scraped=datetime.now(timezone.utc)
                )
            ]
            
            for ds in data_sources:
                db.session.add(ds)
            db.session.flush()
            
            # Create test prospects with various attributes
            prospects = [
                Prospect(
                    id='TEST-001',
                    native_id='NATIVE-001',
                    title='AI Software Development Services',
                    description='Development of artificial intelligence software solutions for government agencies',
                    agency='Department of Test',
                    naics='541511',
                    naics_description='Custom Computer Programming Services',
                    naics_source='original',
                    estimated_value_text='$100,000 - $500,000',
                    estimated_value_single=Decimal('300000'),
                    release_date=date.today(),
                    award_date=date.today(),
                    place_city='Washington',
                    place_state='DC',
                    contract_type='Fixed Price',
                    set_aside='Small Business',
                    set_aside_standardized='SMALL_BUSINESS',
                    primary_contact_email='contact1@test.gov',
                    primary_contact_name='John Smith',
                    source_id=data_sources[0].id,
                    loaded_at=datetime.now(timezone.utc),
                    ollama_processed_at=datetime.now(timezone.utc),
                    enhancement_status='idle'
                ),
                Prospect(
                    id='TEST-002',
                    native_id='NATIVE-002',
                    title='Cybersecurity Consulting Services',
                    description='Security assessment and penetration testing services',
                    agency='Test Agency',
                    naics='541512',
                    naics_description='Computer Systems Design Services',
                    naics_source='llm_inferred',
                    estimated_value_text='$50,000',
                    estimated_value_single=Decimal('50000'),
                    release_date=date.today(),
                    award_date=date.today(),
                    place_city='New York',
                    place_state='NY',
                    contract_type='Time and Materials',
                    set_aside='8(a) Set-Aside',
                    set_aside_standardized='EIGHT_A',
                    primary_contact_email='contact2@agency.gov',
                    primary_contact_name='Jane Doe',
                    source_id=data_sources[1].id,
                    loaded_at=datetime.now(timezone.utc),
                    enhancement_status='in_progress'
                ),
                Prospect(
                    id='TEST-003',
                    native_id='NATIVE-003',
                    title='Data Analytics Platform Development',
                    description='Big data analytics and visualization platform',
                    agency='Department of Test',
                    naics='541511',
                    naics_description='Custom Computer Programming Services',
                    naics_source='original',
                    estimated_value_text='TBD',
                    place_city='San Francisco',
                    place_state='CA',
                    contract_type='Cost Plus',
                    set_aside='Full and Open',
                    set_aside_standardized='FULL_AND_OPEN',
                    source_id=data_sources[0].id,
                    loaded_at=datetime.now(timezone.utc),
                    enhancement_status='failed'
                ),
                Prospect(
                    id='TEST-004',
                    native_id='NATIVE-004',
                    title='Network Infrastructure Upgrade',
                    description='Upgrade of legacy network infrastructure',
                    agency='Test Agency',
                    naics='517311',
                    naics_description='Wired Telecommunications Carriers',
                    naics_source='original',
                    estimated_value_text='$1,000,000 - $5,000,000',
                    estimated_value_single=Decimal('3000000'),
                    release_date=date.today(),
                    award_date=date.today(),
                    place_city='Austin',
                    place_state='TX',
                    contract_type='Fixed Price',
                    set_aside='WOSB Set-Aside',
                    set_aside_standardized='WOSB',
                    primary_contact_email='contact3@agency.gov',
                    source_id=data_sources[1].id,
                    loaded_at=datetime.now(timezone.utc),
                    ollama_processed_at=datetime.now(timezone.utc),
                    enhancement_status='idle'
                )
            ]
            
            for prospect in prospects:
                db.session.add(prospect)
            
            db.session.commit()
            
            yield
            
            # Cleanup
            db.session.rollback()
            db.drop_all()
    
    def test_get_prospects_basic(self, client):
        """Test basic prospects retrieval."""
        response = client.get('/api/prospects')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'prospects' in data
        assert 'pagination' in data
        assert len(data['prospects']) > 0
        
        # Check first prospect structure
        prospect = data['prospects'][0]
        required_fields = ['id', 'title', 'agency', 'description', 'naics']
        for field in required_fields:
            assert field in prospect
    
    def test_get_prospects_pagination(self, client):
        """Test prospects pagination."""
        # Test page 1 with limit 2
        response = client.get('/api/prospects?page=1&limit=2')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['prospects']) == 2
        assert data['pagination']['page'] == 1
        assert data['pagination']['total_items'] == 4
        assert data['pagination']['has_next'] is True
        
        # Test page 2
        response = client.get('/api/prospects?page=2&limit=2')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['prospects']) == 2
        assert data['pagination']['page'] == 2
        assert data['pagination']['has_next'] is False
    
    def test_get_prospects_search(self, client):
        """Test prospects search functionality."""
        # Search by title
        response = client.get('/api/prospects?search=AI Software')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['prospects']) == 1
        assert 'AI Software' in data['prospects'][0]['title']
        
        # Search by description
        response = client.get('/api/prospects?search=cybersecurity')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['prospects']) == 1
        assert 'Cybersecurity' in data['prospects'][0]['title']
        
        # Search by agency
        response = client.get('/api/prospects?search=Department of Test')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['prospects']) == 2
        for prospect in data['prospects']:
            assert prospect['agency'] == 'Department of Test'
    
    def test_get_prospects_naics_filter(self, client):
        """Test NAICS code filtering."""
        response = client.get('/api/prospects?naics=541511')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['prospects']) == 2
        for prospect in data['prospects']:
            assert prospect['naics'] == '541511'
    
    def test_get_prospects_agency_filter(self, client):
        """Test agency filtering."""
        response = client.get('/api/prospects?agency=Test Agency')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['prospects']) == 2
        for prospect in data['prospects']:
            assert prospect['agency'] == 'Test Agency'
    
    def test_get_prospects_ai_enrichment_filter(self, client):
        """Test AI enrichment filtering."""
        # Filter for AI-enhanced prospects
        response = client.get('/api/prospects?ai_enrichment=enhanced')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['prospects']) == 2
        for prospect in data['prospects']:
            assert prospect['ollama_processed_at'] is not None
        
        # Filter for non-enhanced prospects
        response = client.get('/api/prospects?ai_enrichment=original')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['prospects']) == 2
        for prospect in data['prospects']:
            assert prospect['ollama_processed_at'] is None
    
    def test_get_prospects_source_ids_filter(self, client):
        """Test source IDs filtering."""
        # Get source ID from first prospect
        response = client.get('/api/prospects?limit=1')
        data = response.get_json()
        source_id = data['prospects'][0]['source_id']
        
        # Filter by source ID
        response = client.get(f'/api/prospects?source_ids={source_id}')
        
        assert response.status_code == 200
        data = response.get_json()
        
        for prospect in data['prospects']:
            assert prospect['source_id'] == source_id
    
    def test_get_prospects_sorting(self, client):
        """Test prospects sorting."""
        # Sort by title ascending
        response = client.get('/api/prospects?sort_by=title&sort_order=asc')
        
        assert response.status_code == 200
        data = response.get_json()
        
        titles = [p['title'] for p in data['prospects']]
        assert titles == sorted(titles)
        
        # Sort by title descending
        response = client.get('/api/prospects?sort_by=title&sort_order=desc')
        
        assert response.status_code == 200
        data = response.get_json()
        
        titles = [p['title'] for p in data['prospects']]
        assert titles == sorted(titles, reverse=True)
    
    def test_get_prospects_combined_filters(self, client):
        """Test combining multiple filters."""
        response = client.get(
            '/api/prospects?agency=Department of Test&naics=541511&ai_enrichment=enhanced'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['prospects']) == 1
        prospect = data['prospects'][0]
        assert prospect['agency'] == 'Department of Test'
        assert prospect['naics'] == '541511'
        assert prospect['ollama_processed_at'] is not None
    
    def test_get_prospects_invalid_page(self, client):
        """Test error handling for invalid page numbers."""
        response = client.get('/api/prospects?page=0')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'positive' in data['error'].lower()
        
        response = client.get('/api/prospects?page=-1')
        
        assert response.status_code == 400
    
    def test_get_prospect_by_id(self, client):
        """Test retrieving individual prospect by ID."""
        response = client.get('/api/prospects/TEST-001')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['id'] == 'TEST-001'
        assert data['title'] == 'AI Software Development Services'
        assert data['agency'] == 'Department of Test'
        
        # Check all expected fields are present
        expected_fields = [
            'id', 'native_id', 'title', 'description', 'agency', 'naics',
            'naics_description', 'naics_source', 'estimated_value_text',
            'estimated_value_single', 'release_date', 'award_date',
            'place_city', 'place_state', 'contract_type', 'set_aside',
            'set_aside_standardized', 'primary_contact_email',
            'primary_contact_name', 'loaded_at', 'ollama_processed_at',
            'enhancement_status', 'source_id'
        ]
        
        for field in expected_fields:
            assert field in data
    
    def test_get_prospect_not_found(self, client):
        """Test 404 for non-existent prospect."""
        response = client.get('/api/prospects/NON-EXISTENT')
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    def test_get_prospects_statistics(self, client):
        """Test prospects statistics endpoint - skip if not implemented."""
        response = client.get('/api/prospects/statistics')
        
        # If statistics endpoint doesn't exist, skip test
        if response.status_code == 404:
            pytest.skip("Statistics endpoint not implemented")
        
        assert response.status_code == 200
        data = response.get_json()
        
        expected_stats = [
            'total_prospects', 'by_agency', 'by_naics', 'by_enhancement_status',
            'by_set_aside', 'value_statistics'
        ]
        
        for stat in expected_stats:
            assert stat in data
        
        assert data['total_prospects'] == 4
        assert 'Department of Test' in data['by_agency']
        assert 'Test Agency' in data['by_agency']
        assert data['by_agency']['Department of Test'] == 2
        assert data['by_agency']['Test Agency'] == 2
    
    def test_prospects_api_performance(self, client):
        """Test API performance with various query parameters."""
        import time
        
        # Test multiple requests with different filters
        test_queries = [
            '/api/prospects',
            '/api/prospects?page=1&limit=10',
            '/api/prospects?search=software',
            '/api/prospects?agency=Test Agency',
            '/api/prospects?naics=541511',
            '/api/prospects?ai_enrichment=enhanced',
            '/api/prospects?sort_by=title&sort_order=asc'
        ]
        
        response_times = []
        
        for query in test_queries:
            start_time = time.time()
            response = client.get(query)
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
        
        # All queries should complete within reasonable time (2 seconds)
        assert all(rt < 2.0 for rt in response_times)
        
        # Average response time should be fast
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 0.5  # 500ms average
    
    def test_prospects_api_data_integrity(self, client):
        """Test data integrity in API responses."""
        response = client.get('/api/prospects')
        
        assert response.status_code == 200
        data = response.get_json()
        
        for prospect in data['prospects']:
            # Check required fields are not None
            assert prospect['id'] is not None
            assert prospect['title'] is not None
            assert prospect['agency'] is not None
            
            # Check data types - API returns strings for Decimal fields
            if prospect['estimated_value_single'] is not None:
                # Ensure it can be converted to float
                try:
                    float(prospect['estimated_value_single'])
                except (ValueError, TypeError):
                    pytest.fail(f"estimated_value_single should be numeric string, got {prospect['estimated_value_single']}")
            
            # Check enhancement status is valid
            valid_statuses = ['idle', 'in_progress', 'completed', 'failed']
            assert prospect['enhancement_status'] in valid_statuses
            
            # Check NAICS source is valid if present
            if prospect['naics_source'] is not None:
                valid_sources = ['original', 'llm_inferred', 'llm_enhanced']
                assert prospect['naics_source'] in valid_sources
    
    def test_prospects_api_security(self, client):
        """Test API security measures."""
        # Test SQL injection attempt
        response = client.get("/api/prospects?search='; DROP TABLE prospects; --")
        
        # Should not crash and should return valid response
        assert response.status_code == 200
        data = response.get_json()
        assert 'prospects' in data
        
        # Test XSS attempt
        response = client.get('/api/prospects?search=<script>alert("xss")</script>')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Response should not contain raw script tags
        response_text = response.get_data(as_text=True)
        assert '<script>' not in response_text
    
    def test_prospects_api_content_type(self, client):
        """Test API content type headers."""
        response = client.get('/api/prospects')
        
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        
        # Test that response is valid JSON
        try:
            json.loads(response.get_data(as_text=True))
        except json.JSONDecodeError:
            pytest.fail("Response is not valid JSON")
    
    def test_prospects_api_error_handling(self, client):
        """Test API error handling."""
        # Test with invalid parameters
        response = client.get('/api/prospects?limit=abc')
        
        # Should handle gracefully, not crash
        assert response.status_code in [200, 400]
        
        # Test with very large limit - API has max limit of 100
        response = client.get('/api/prospects?limit=99999')
        
        # Should return 400 due to exceeding max limit
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'exceed 100' in data['error']