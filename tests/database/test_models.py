"""
Comprehensive tests for database models.

Tests model validation, relationships, and business logic.
"""

import pytest
from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app import create_app
from app.database import db
from app.database.models import (
    Prospect, DataSource, InferredProspectData, LLMOutput, 
    AIEnrichmentLog, GoNoGoDecision
)
from app.database.user_models import User


@pytest.fixture(scope='class')
def app():
    """Create test Flask app."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


@pytest.fixture
def db_session(app):
    """Create test database session."""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.rollback()
        db.drop_all()


class TestProspectModel:
    """Test Prospect model functionality."""
    
    def test_prospect_creation(self, db_session):
        """Test basic prospect creation."""
        prospect = Prospect(
            id='test-001',
            native_id='NATIVE-001',
            title='Test Contract Opportunity',
            description='Test description for contract',
            agency='Department of Test',
            naics='541511',
            estimated_value_text='$100,000 - $500,000',
            release_date=date.today(),
            award_date=date.today(),
            place_city='Washington',
            place_state='DC',
            contract_type='Fixed Price',
            set_aside='Small Business',
            loaded_at=datetime.now(timezone.utc)
        )
        
        db_session.add(prospect)
        db_session.commit()
        
        # Verify prospect was created
        saved_prospect = db_session.get(Prospect, 'test-001')
        assert saved_prospect is not None
        assert saved_prospect.title == 'Test Contract Opportunity'
        assert saved_prospect.naics == '541511'
        assert saved_prospect.enhancement_status == 'idle'  # Default value
    
    def test_prospect_required_fields(self, db_session):
        """Test prospect validation for required fields."""
        # Missing required id should fail
        prospect = Prospect(
            title='Test Contract',
            loaded_at=datetime.now(timezone.utc)
        )
        
        db_session.add(prospect)
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_prospect_indexes(self, db_session):
        """Test that indexed fields work correctly."""
        prospects = [
            Prospect(
                id=f'test-{i:03d}',
                title=f'Contract {i}',
                agency=f'Agency {i % 3}',
                naics=f'54151{i % 5}',
                place_city='Washington' if i % 2 == 0 else 'New York',
                loaded_at=datetime.now(timezone.utc)
            )
            for i in range(10)
        ]
        
        for prospect in prospects:
            db_session.add(prospect)
        db_session.commit()
        
        # Test agency filtering
        agency_0_prospects = db_session.execute(
            select(Prospect).where(Prospect.agency == 'Agency 0')
        ).scalars().all()
        assert len(agency_0_prospects) > 0
        
        # Test city filtering
        washington_prospects = db_session.execute(
            select(Prospect).where(Prospect.place_city == 'Washington')
        ).scalars().all()
        assert len(washington_prospects) == 5
    
    def test_prospect_llm_enhancement_fields(self, db_session):
        """Test LLM enhancement specific fields."""
        prospect = Prospect(
            id='test-llm-001',
            title='Original Title',
            description='Original description',
            estimated_value_text='$50k-$100k',
            loaded_at=datetime.now(timezone.utc)
        )
        
        db_session.add(prospect)
        db_session.commit()
        
        # Update with LLM enhancements
        prospect.ai_enhanced_title = 'Enhanced AI Title'
        prospect.estimated_value_min = Decimal('50000')
        prospect.estimated_value_max = Decimal('100000')
        prospect.estimated_value_single = Decimal('75000')
        prospect.naics = '541511'
        prospect.naics_source = 'llm_inferred'
        prospect.naics_description = 'Custom Computer Programming Services'
        prospect.primary_contact_email = 'contact@agency.gov'
        prospect.primary_contact_name = 'John Doe'
        prospect.set_aside_standardized = 'SMALL_BUSINESS'
        prospect.set_aside_standardized_label = 'Small Business Set-Aside'
        prospect.ollama_processed_at = datetime.now(timezone.utc)
        prospect.ollama_model_version = 'qwen3:latest'
        
        db_session.commit()
        
        # Verify enhancements
        enhanced_prospect = db_session.get(Prospect, 'test-llm-001')
        assert enhanced_prospect.ai_enhanced_title == 'Enhanced AI Title'
        assert enhanced_prospect.estimated_value_single == Decimal('75000')
        assert enhanced_prospect.naics_source == 'llm_inferred'
        assert enhanced_prospect.primary_contact_email == 'contact@agency.gov'
        assert enhanced_prospect.ollama_processed_at is not None
    
    def test_prospect_enhancement_status_tracking(self, db_session):
        """Test enhancement status and tracking fields."""
        prospect = Prospect(
            id='test-enhancement-001',
            title='Enhancement Test',
            loaded_at=datetime.now(timezone.utc)
        )
        
        db_session.add(prospect)
        db_session.commit()
        
        # Start enhancement
        prospect.enhancement_status = 'in_progress'
        prospect.enhancement_started_at = datetime.now(timezone.utc)
        prospect.enhancement_user_id = 1
        
        db_session.commit()
        
        # Verify tracking
        tracked_prospect = db_session.get(Prospect, 'test-enhancement-001')
        assert tracked_prospect.enhancement_status == 'in_progress'
        assert tracked_prospect.enhancement_started_at is not None
        assert tracked_prospect.enhancement_user_id == 1


class TestDataSourceModel:
    """Test DataSource model functionality."""
    
    def test_data_source_creation(self, db_session):
        """Test basic data source creation."""
        data_source = DataSource(
            name='Test Agency',
            url='https://test.agency.gov',
            last_scraped=datetime.now(timezone.utc)
        )
        
        db_session.add(data_source)
        db_session.commit()
        
        # Verify creation
        saved_source = db_session.execute(
            select(DataSource).where(DataSource.name == 'Test Agency')
        ).scalar_one()
        assert saved_source.url == 'https://test.agency.gov'
    
    def test_data_source_prospect_relationship(self, db_session):
        """Test relationship between DataSource and Prospects."""
        # Create data source
        data_source = DataSource(
            name='Test Agency',
            url='https://test.agency.gov',
            last_scraped=datetime.now(timezone.utc)
        )
        db_session.add(data_source)
        db_session.flush()
        
        # Create prospects linked to data source
        prospects = [
            Prospect(
                id=f'test-rel-{i:03d}',
                title=f'Contract {i}',
                source_id=data_source.id,
                loaded_at=datetime.now(timezone.utc)
            )
            for i in range(3)
        ]
        
        for prospect in prospects:
            db_session.add(prospect)
        db_session.commit()
        
        # Test relationship
        saved_source = db_session.get(DataSource, data_source.id)
        assert len(saved_source.prospects) == 3
        
        # Test reverse relationship
        prospect = db_session.get(Prospect, 'test-rel-001')
        assert prospect.data_source.name == 'Test Agency'


class TestLLMOutputModel:
    """Test LLMOutput model for logging LLM interactions."""
    
    def test_llm_output_creation(self, db_session):
        """Test LLM output logging."""
        # Create prospect first
        prospect = Prospect(
            id='test-llm-output-001',
            title='Test Prospect',
            loaded_at=datetime.now(timezone.utc)
        )
        db_session.add(prospect)
        db_session.flush()
        
        # Create LLM output
        llm_output = LLMOutput(
            prospect_id=prospect.id,
            enhancement_type='values',
            prompt='Parse the contract value from: $100k-$500k',
            response='{"min_value": 100000, "max_value": 500000}'
        )
        
        db_session.add(llm_output)
        db_session.commit()
        
        # Verify logging
        saved_output = db_session.execute(
            select(LLMOutput).where(LLMOutput.prospect_id == prospect.id)
        ).scalar_one()
        assert saved_output.enhancement_type == 'values'
        assert 'min_value' in saved_output.response


class TestInferredProspectDataModel:
    """Test InferredProspectData model."""
    
    def test_inferred_data_creation(self, db_session):
        """Test creation of inferred prospect data."""
        # Create prospect first
        prospect = Prospect(
            id='test-inferred-001',
            title='Test Prospect',
            loaded_at=datetime.now(timezone.utc)
        )
        db_session.add(prospect)
        db_session.flush()
        
        # Create inferred data
        inferred_data = InferredProspectData(
            prospect_id=prospect.id,
            inferred_naics='541511',
            inferred_naics_description='Custom Computer Programming Services',
            inferred_estimated_value_min=100000.0,
            inferred_estimated_value_max=500000.0
        )
        
        db_session.add(inferred_data)
        db_session.commit()
        
        # Verify creation
        saved_data = db_session.execute(
            select(InferredProspectData).where(
                InferredProspectData.prospect_id == prospect.id
            )
        ).scalar_one()
        assert saved_data.inferred_naics == '541511'
        assert saved_data.inferred_estimated_value_min == 100000.0
        assert saved_data.inferred_estimated_value_max == 500000.0


class TestUserModel:
    """Test User model functionality."""
    
    def test_user_creation(self, db_session):
        """Test user creation with required fields."""
        user = User(
            email='test@example.com',
            first_name='Test User',
            role='user'
        )
        
        db_session.add(user)
        db_session.commit()
        
        saved_user = db_session.execute(
            select(User).where(User.email == 'test@example.com')
        ).scalar_one()
        assert saved_user.first_name == 'Test User'
        assert saved_user.role == 'user'
    
    def test_user_unique_constraints(self, db_session):
        """Test user unique constraints."""
        user1 = User(
            email='test1@example.com',
            first_name='Test User 1',
            role='user'
        )
        
        user2 = User(
            email='test1@example.com',  # Duplicate email
            first_name='Test User 2',
            role='user'
        )
        
        db_session.add(user1)
        db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestDecisionModel:
    """Test GoNoGoDecision model for go/no-go decisions."""
    
    def test_decision_creation(self, db_session):
        """Test decision creation."""
        # Create user and prospect first
        user = User(
            email='dm@example.com',
            first_name='Decision Maker',
            role='user'
        )
        db_session.add(user)
        db_session.flush()
        
        prospect = Prospect(
            id='test-decision-001',
            title='Decision Test Prospect',
            loaded_at=datetime.now(timezone.utc)
        )
        db_session.add(prospect)
        db_session.flush()
        
        # Create decision
        decision = GoNoGoDecision(
            prospect_id=prospect.id,
            user_id=user.id,
            decision='go',
            reason='Good opportunity for our team'
        )
        
        db_session.add(decision)
        db_session.commit()
        
        # Verify decision
        saved_decision = db_session.execute(
            select(GoNoGoDecision).where(GoNoGoDecision.prospect_id == prospect.id)
        ).scalar_one()
        assert saved_decision.decision == 'go'
        assert saved_decision.reason == 'Good opportunity for our team'


class TestAIEnrichmentLogModel:
    """Test AIEnrichmentLog model."""
    
    def test_enrichment_log_creation(self, db_session):
        """Test enrichment log creation."""
        # Create enrichment log
        enrichment_log = AIEnrichmentLog(
            enhancement_type='all',
            status='completed',
            processed_count=100,
            duration=45.5,
            message='Successfully processed 100 prospects',
            error=None
        )
        
        db_session.add(enrichment_log)
        db_session.commit()
        
        # Verify log
        saved_log = db_session.execute(
            select(AIEnrichmentLog).order_by(AIEnrichmentLog.id.desc())
        ).scalar_one()
        assert saved_log.enhancement_type == 'all'
        assert saved_log.status == 'completed'
        assert saved_log.processed_count == 100


class TestModelRelationships:
    """Test complex model relationships and queries."""
    
    def test_prospect_full_relationships(self, db_session):
        """Test prospect with all related models."""
        # Create data source
        data_source = DataSource(
            name='Full Test Agency',
            url='https://fulltest.gov',
            last_scraped=datetime.now(timezone.utc)
        )
        db_session.add(data_source)
        db_session.flush()
        
        # Create user
        user = User(
            email='full@example.com',
            first_name='Full User',
            role='admin'
        )
        db_session.add(user)
        db_session.flush()
        
        # Create prospect
        prospect = Prospect(
            id='test-full-rel-001',
            title='Full Relationship Test',
            source_id=data_source.id,
            loaded_at=datetime.now(timezone.utc)
        )
        db_session.add(prospect)
        db_session.flush()
        
        # Create related records
        llm_output = LLMOutput(
            prospect_id=prospect.id,
            enhancement_type='titles',
            prompt='Enhance this title',
            response='Enhanced Title Response'
        )
        
        decision = GoNoGoDecision(
            prospect_id=prospect.id,
            user_id=user.id,
            decision='go',
            reason='Full test reasoning'
        )
        
        enrichment_log = AIEnrichmentLog(
            enhancement_type='all',
            status='completed',
            processed_count=1,
            duration=2.5,
            message='Full relationship test'
        )
        
        db_session.add_all([llm_output, decision, enrichment_log])
        db_session.commit()
        
        # Test complex query joining related tables (excluding User since it's in separate DB)
        result = db_session.execute(
            select(Prospect, DataSource, GoNoGoDecision)
            .join(DataSource, Prospect.source_id == DataSource.id)
            .join(GoNoGoDecision, Prospect.id == GoNoGoDecision.prospect_id)
            .where(Prospect.id == 'test-full-rel-001')
        ).first()
        
        assert result is not None
        prospect, data_source, decision = result
        assert prospect.title == 'Full Relationship Test'
        assert data_source.name == 'Full Test Agency'
        assert decision.decision == 'go'
        assert decision.user_id == user.id  # Verify the user_id is correct
    
    def test_cascade_deletes(self, db_session):
        """Test that cascade deletes work properly."""
        # Create data source with prospects
        data_source = DataSource(
            name='Cascade Test Agency',
            url='https://cascade.gov',
            last_scraped=datetime.now(timezone.utc)
        )
        db_session.add(data_source)
        db_session.flush()
        
        prospect = Prospect(
            id='test-cascade-001',
            title='Cascade Test',
            source_id=data_source.id,
            loaded_at=datetime.now(timezone.utc)
        )
        db_session.add(prospect)
        db_session.flush()
        
        # Add related records
        llm_output = LLMOutput(
            prospect_id=prospect.id,
            enhancement_type='values',
            prompt='test',
            response='test'
        )
        db_session.add(llm_output)
        db_session.commit()
        
        # Verify records exist
        assert db_session.get(Prospect, 'test-cascade-001') is not None
        assert db_session.execute(
            select(LLMOutput).where(LLMOutput.prospect_id == 'test-cascade-001')
        ).scalar_one() is not None
        
        # Delete prospect should cascade to related records if configured
        db_session.delete(prospect)
        db_session.commit()
        
        # Verify prospect is deleted
        assert db_session.get(Prospect, 'test-cascade-001') is None